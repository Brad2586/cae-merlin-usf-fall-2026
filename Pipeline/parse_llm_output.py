import json
import re
import struct
import time
from logger import log

class LLMOutputParser:
    def __init__(
        self,
        communication_client,
        host_dict,
        llm,
        audio_pipeline,
        tts,
        exit_handler,
        mappings=None,
        alias_to_name=None,
        status_store=None,
    ):
        self.communication_client = communication_client
        self.host_dict = host_dict
        self.llm = llm
        self.audio_pipeline = audio_pipeline
        self.tts = tts
        self.exit_handler = exit_handler
        self.status_store = status_store

        # Mapping-related
        self.mappings = mappings or []       # list of mapping dicts
        self.alias_to_name = alias_to_name or {}  # alias -> canonical name

    def check_host_value(self, var_name, desired_bytes, dimensions=None):
        """
        Compare a current host value with the requested value.

        Supports scalar variables and indexed arrays.
        """
        var_meta = self.host_dict[var_name]
        num_dims = int(var_meta.get("num_dims", 0) or 0)
        sizes = list(var_meta.get("dimensions", []))
        indices = list(dimensions or [])

        variables = [{
            "name": var_name,
            "index": var_meta["index"],
            "type": var_meta["type"],
            "num_dims": num_dims,
            "dimensions": sizes
        }]

        # Validate dimensions before contacting the host.
        if num_dims != len(indices):
            return "unknown"

        if num_dims != len(sizes):
            return "unknown"

        for index, size in zip(indices, sizes):
            if not isinstance(index, int) or not (0 <= index < size):
                return "unknown"

        try:
            updates = self.communication_client.request_update(
                var_meta["list_type"], variables
            )

            if var_name not in updates:
                return "unknown"

            current_bytes = updates[var_name]["value"]

            if num_dims > 0:
                element_size = len(desired_bytes)
                total_elements = 1

                for size in sizes:
                    total_elements *= size

                if len(current_bytes) != total_elements * element_size:
                    return "unknown"

                # Row-major element offset.
                flat_index = 0
                for index, size in zip(indices, sizes):
                    flat_index = flat_index * size + index

                start = flat_index * element_size
                current_bytes = current_bytes[
                    start:start + element_size
                ]

            elif len(current_bytes) != len(desired_bytes):
                return "unknown"

            return (
                "same" if current_bytes == desired_bytes
                else "different"
            )

        except (OSError, ValueError, IndexError, KeyError, TypeError) as e:
            print(f"[R2] Failed to read {var_name}: {e}")
            return "unknown"

    def set_variable_if_changed(
        self, var_name, desired_bytes, dimensions=None
    ):
        """
        R2: Only send a SET command if the host value differs.

        Returns:
            "skipped" - Already correct
            "sent"    - SET command issued
            "failed"  - Unable to verify or send
        """
        result = self.check_host_value(
            var_name,
            desired_bytes,
            dimensions=dimensions
        )

        print(f"[R2 LIVE] {var_name}: comparison={result}")

        if result == "unknown":
            return "failed"

        if result == "same":
            return "skipped"

        meta = self.host_dict[var_name]

        try:
            self.communication_client.set_variable(
                meta["list_type"],
                meta["index"],
                value=desired_bytes,
                dimensions=dimensions or [],
            )
        except (OSError, ConnectionError):
            return "failed"

        return "sent"

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    def _get_mappings_for_alias(self, alias_name: str):
        """Return all mapping entries matching a given alias."""
        if not self.mappings or not alias_name:
            return []
        alias_name = alias_name.strip()
        result = []
        for m in self.mappings:
            a = (m.get("alias") or "").strip()
            if a == alias_name:
                result.append(m)
        return result

    # Might not need this function
    def find_mapping_for_command(self, command_name):
        """Find mapping entry whose command_name matches the given string (case-insensitive)."""
        if not self.mappings:
            return None
        command_name_lower = command_name.strip().lower()
        for m in self.mappings:
            if m["command_name"].lower() == command_name_lower:
                return m
        return None

    def resolve_var_key(self, key: str) -> str | None:
        """
        Resolve a variable key from LLM (can be alias or canonical name)
        to the canonical name used in host_dict.
        """
        if not key:
            return None
        key = key.strip()
        # First try alias map
        if key in self.alias_to_name:
            resolved = self.alias_to_name[key]
            return resolved

        # Fallback: if host_dict already has this key, accept it
        if key in self.host_dict:
            return key

        return None

    # ------------------------------------------------------------------
    # General helpers
    # ------------------------------------------------------------------

    def _say(self, message, priority="normal"):
        self.tts.say(message, priority=priority)

    def _record_change(self, variable, value, common_name):
        if self.status_store is None:
            return
        try:
            self.status_store.record_change(
                variable,
                value,
                display_name=common_name,
            )
        except OSError as exc:
            log("[STATUS]", f"Unable to record requested change: {exc}")

    def send_variable_updates(self, pairs, list_type=1):
        """
        Send multiple variable updates to the simulator.

        pairs: list of (var_index, value_bytes) tuples.
               var_index: integer index assigned by create_update_page
               value_bytes: already-encoded bytes for the variable value
        list_type: simulator list type (usually 1 for 'update page' variables).
        """
        for var_index, value_bytes in pairs:
            self.communication_client.set_variable(
                list_type=list_type,
                var_index=var_index,
                value=value_bytes
            )

    # ------------------------------------------------------------------
    # Main parsing
    # ------------------------------------------------------------------

    def parse_LLM_output(self, LLM_Output, pending_pairs=None):
        if pending_pairs is None:
            pending_pairs = []

        match = re.search(r'\{.*\}', LLM_Output)
        if not match:
            log("[JSON_ERROR]", "Not enough tokens or json didn't generate properly")
            self._say("Not enough tokens or json didn't generate properly", priority="critical")
            return False

        data = json.loads(match.group())
        command_type = data.get("Type")

        match command_type:
            case "command":
                keys = data.get("parameters_keys", [])
                values = data.get("parameters_values", [])
                meta_list = data.get("parameters_meta", []) or []

                key_to_indices: dict[str, list[int] | None] = {}
                for meta in meta_list:
                    try:
                        m_key = meta.get("key")
                        if not m_key:
                            continue
                        idxs = meta.get("indices")
                        if idxs is not None:
                            key_to_indices[m_key] = [int(i) for i in idxs]
                        else:
                            key_to_indices[m_key] = None
                    except Exception:
                        continue

                all_pairs = []
                for key, value in zip(keys, values):
                    # Resolve alias to base host_dict name
                    resolved_name = self.resolve_var_key(key)
                    if not resolved_name:
                        log("[VARIABLE_ERROR]", f"Unknown alias/key from LLM: {key}")
                        continue

                    indices = key_to_indices.get(key)  # may be None
                    # Store both alias key and resolved name
                    all_pairs.append((key, resolved_name, value, indices))

                # Include any pending pairs (backwards compatibility: they won't have indices)
                for item in pending_pairs:
                    if isinstance(item, tuple) and len(item) == 3:
                        all_pairs.append(item)
                    elif isinstance(item, tuple) and len(item) == 2:
                        all_pairs.append((item[0], item[1], None))
                    else:
                        # Fallback if older code passed something unexpected
                        try:
                            k, v = item
                            all_pairs.append((k, v, None))
                        except Exception:
                            continue

                set_count = 0
                for alias_key, base_name, value, indices in all_pairs:
                    if self.set_llm_variable(base_name, value, indices=indices, alias_name=alias_key):
                        set_count += 1

                return True

            case "clarification":
                # Accumulate known params but don't send yet
                keys = data.get("parameters_keys") or []
                values = data.get("parameters_values") or []
                # Note: pending_pairs for clarifications will not carry indices yet,
                # but parse_LLM_output will handle that gracefully.
                accumulated_pairs = pending_pairs + list(zip(keys, values))

                # Ask for clarification, passing accumulated pairs through
                handled = self.get_clarification(data.get("message"), accumulated_pairs)
                if not handled:
                    return False

                return True

            case "error":
                self._say(data.get("message"), priority="critical")
                return False

            case "exit":
                self._say("Exiting the program.", priority="critical")
                self.exit_handler.exit_program()

            case "mode_strict":
                from config.config import set_mode
                set_mode("strict")
                if self.status_store is not None:
                    self.status_store.update(active_model="strict")
                self._say("Mode changed to strict.", priority="normal")

            case "mode_lenient":
                from config.config import set_mode
                set_mode("lenient")
                if self.status_store is not None:
                    self.status_store.update(active_model="lenient")
                self._say("Mode changed to lenient.", priority="normal")

    # ------------------------------------------------------------------

    def get_clarification(self, message, pending_pairs=None):
        if pending_pairs is None:
            pending_pairs = []

        self._say(f"Clarification needed: {message}", priority="critical")
        log("[CLARIFICATION]", "Asking for clarification: " + message)
        
        text = self.audio_pipeline.listen_and_transcribe()
        prompt = f"input: {message} {text}\noutput:"
        llm_output = self.llm.generate_from_llm(prompt, 70)

        # Pass accumulated pairs into the next parse so they all send together
        self.parse_LLM_output(llm_output, pending_pairs)
        return True

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def get_range_config(self):
        """Load variable_range from config each call so hot-edits take effect."""
        from config.config import get_variable_ranges
        return get_variable_ranges()
 
    def validate_value(self, var_name, type_code, value, common_name):
        """
        Validate *value* against the rules in config.json's variable_range block
        and any hard-coded dependency rules.
 
        Returns (ok: bool, error_message: str | None).
        """
 
        ranges = self.get_range_config()
 
        TYPE_CHAR   = 0
        TYPE_FLOAT  = 5
        TYPE_DOUBLE = 6
 
        # ---- CHAR: allowlist check ----
        if type_code == TYPE_CHAR:
            allowlists = ranges.get("char", {})
            if var_name in allowlists:
                allowed = allowlists[var_name]
                if value not in allowed:
                    return (
                        False,
                        f"Invalid value for {common_name}: '{value}' is not a recognised code. "
                        f"Allowed values: {', '.join(allowed)}."
                    )
 
        # ---- FLOAT: numeric range check ----
        elif type_code == TYPE_FLOAT:
            float_ranges = ranges.get("float", {})
            if var_name in float_ranges:
                lo, hi = float_ranges[var_name]
                try:
                    numeric = float(value)
                except (TypeError, ValueError):
                    return False, f"Expected a number for {common_name}, got: {value}"
                if not (lo <= numeric <= hi):
                    return (
                        False,
                        f"Value {numeric} is out of range for {common_name}. "
                        f"Must be between {lo} and {hi}."
                    )
 
        # ---- DOUBLE: numeric range check ----
        elif type_code == TYPE_DOUBLE:
            double_ranges = ranges.get("double", {})
            if var_name in double_ranges:
                lo, hi = double_ranges[var_name]
                try:
                    numeric = float(value)
                except (TypeError, ValueError):
                    return False, f"Expected a number for {common_name}, got: {value}"
                if not (lo <= numeric <= hi):
                    return (
                        False,
                        f"Value {numeric} is out of range for {common_name}. "
                        f"Must be between {lo} and {hi}."
                    )
 
        return True, None
 
    # ------------------------------------------------------------------
    # Array alias inference
    # ------------------------------------------------------------------

    def _infer_array_indices(self, alias_name):
        """Infer underlying array variable and indices from an alias.

        This is primarily used for engine flameout variables where the
        XML defines a single array variable, e.g. MALF.FLAME_OUT with
        dims="4", addressed by ENGINE_1_FLAME, ENGINE_2_FLAME, etc.

        Returns:
            tuple (base_var_name, indices_list) or None if no mapping.
        """

        # Example: ENGINE_n_FLAME aliases to MALF.FLAME_OUT[n-1]
        m = re.match(r"ENGINE_(\d+)_FLAME", alias_name)
        if m:
            engine_num = int(m.group(1))
            # Array index is zero-based
            idx = engine_num - 1
            base_name = "MALF.FLAME_OUT"
            return base_name, [idx]

        return None
 
    # ------------------------------------------------------------------
    # Variable setter with dimensions
    # ------------------------------------------------------------------

    def set_llm_variable(self, var_name, value, list_type=0, indices=None, alias_name=None):
        # Some LLM keys may be aliases that refer to a specific element of an
        # underlying array variable. For example:
        #   ENGINE_1_FLAME -> MALF.FLAME_OUT[0]
        #   ENGINE_2_FLAME -> MALF.FLAME_OUT[1]
        # We use host_dict's num_dims/dimensions metadata to determine how to
        # target the correct array element when calling set_variable.

        original_name = alias_name or var_name

        # Normalize string values from LLM before any custom logic
        if isinstance(value, str):
            v_lower = value.lower()
            if v_lower in ("true", "1", "on", "activate", "enabled"):
                value_bool = True
            elif v_lower in ("false", "0", "off", "deactivate", "disabled"):
                value_bool = False
            else:
                value_bool = None
        elif isinstance(value, bool):
            value_bool = value
        else:
            value_bool = None

        # --- MAPPING-DRIVEN LOGIC (from mapping.xml) ---
        # If there is a mapping for this alias, we honor it.
        if alias_name:
            alias_mappings = self._get_mappings_for_alias(alias_name)
        else:
            alias_mappings = []
        # print("DEBUG: alias_mappings for", alias_name, "=", alias_mappings)

        if alias_mappings:
            if value_bool is True:
                requested_action = "enable"
            elif value_bool is False:
                requested_action = "disable"
            else:
                self._say("Could not determine whether to enable or disable.")
                return False

            matches = [
                mapping
                for mapping in alias_mappings
                if mapping.get("action") == requested_action
            ]

            print("matches: ", matches)

            if len(matches) != 1:
                self._say("Could not find one matching command configuration.")
                return False

            m = matches[0]

            target_var = m["variable"]      # e.g. "MALF_IF.TOGGLE_REQ"
            malf_value = m["value"]         # e.g. 331
            idx = m["index"]                # e.g. 0 (array index) or None
            delay = m.get("time")           # e.g. 0.3, or None

            if target_var not in self.host_dict:
                log("[VARIABLE_ERROR]", f"{target_var} not found in dictionary")
                self._say(f"{target_var} not found in dictionary", priority="critical")
                return False

            var_meta    = self.host_dict[target_var]
            var_index   = var_meta["index"]
            type_code   = var_meta.get("type", 3)
            common_name = var_meta.get("common_name", target_var)
            list_type   = var_meta.get("list_type", list_type)

            # Encode malf_value according to type. Flameout flags are booleans.
            # Instructor toggle requests are int32 codes.
            try:
                if type_code == 1:  # boolean / int8
                    value_bytes = b"\x01" if int(malf_value) else b"\x00"
                elif type_code == 3:  # INT32
                    value_bytes = int(malf_value).to_bytes(4, "little", signed=True)
                else:
                    raise ValueError(f"Unsupported type_code {type_code} for mapped command")
            except Exception as e:
                log("[VALUE_ERROR]", f"{common_name}: {str(e)} (value={malf_value})")
                self._say(f"Invalid mapped value for {common_name}: {malf_value}", priority="critical")
                return False

            # Handle optional index as dimensions if target_var is an array
            num_dims = int(var_meta.get("num_dims", 0) or 0)
            dims = list(var_meta.get("dimensions", [])) if num_dims > 0 else []

            index_list = []
            if num_dims > 0:
                index_list = [idx] if idx is not None else [0]

                for dim_idx, i in enumerate(index_list):
                    max_size = dims[dim_idx] if dim_idx < len(dims) else None
                    if max_size is not None and not (0 <= i < max_size):
                        log("[INDEX_ERROR]", f"Index {i} out of range for {target_var} dimension {dim_idx} (size {max_size})")
                        self._say(f"Index out of range for {common_name}", priority="critical")
                        return False

            # Check Before Set
            result = self.set_variable_if_changed(
                var_name,
                value_bytes,
                dimensions=index_list
            )

            if result == "skipped":
                log("[R2]", f"Skipped {var_name}: already at requested value")
                self._say(
                    f"{common_name} is already set to {value}",
                    priority="bulk"
                )
                return True

            if result == "failed":
                log("[R2]", f"Unable to verify or set {var_name}")
                self._say(
                    f"Unable to verify or set {common_name}",
                    priority="critical"
                )
                return False

            # Send mapped value
            try:
                self.communication_client.set_variable(
                    list_type,
                    var_index,
                    dimensions=index_list,
                    value=value_bytes,
                )
            except TypeError:
                # client without dimensions parameter
                try:
                    self.communication_client.set_variable(
                        list_type,
                        var_index,
                        value=value_bytes,
                    )
                except (OSError, ConnectionAbortedError) as e:
                    log("[SOCKET_ERROR]", f"Set {target_var} failed: {e}")
                    self._say("Lost connection to simulator while setting a malfunction.", priority="critical")
                    return False
            except (OSError, ConnectionAbortedError) as e:
                log("[SOCKET_ERROR]", f"Set {target_var} failed: {e}")
                self._say("Lost connection to simulator while setting a malfunction.", priority="critical")
                return False

            log("[SET_VARIABLE]", f"Mapped command: Set {target_var} (type_code={type_code}) to {malf_value}")
            self._record_change(target_var, malf_value, common_name)
            self._say(f"Set {common_name} to mapped value {malf_value}", priority="bulk")

            # Optional time delay for this mapped command, if configured in mappings file
            if delay is not None and delay > 0:
                time.sleep(delay)

            return True

        # Type code constants (matching TYPE_CODE_MAP in load_variables)
        TYPE_CHAR    = 0
        TYPE_INT8    = 1
        TYPE_INT16   = 2
        TYPE_INT32   = 3
        TYPE_INT64   = 4
        TYPE_FLOAT   = 5
        TYPE_DOUBLE  = 6
        TYPE_POINTER = 7

        # # If indices are not provided explicitly, attempt to infer them from alias
        # if indices is None and alias_name is not None:
        #     inferred = self._infer_array_indices(alias_name)
        #     if inferred is not None:
        #         base_name, inferred_indices = inferred
        #         var_name = base_name
        #         indices = inferred_indices
 
        if var_name not in self.host_dict:
            log("[VARIABLE_ERROR]", f"{var_name} not found in dictionary")
            self._say(f"{original_name} not found in dictionary", priority="critical")
            return False
 
        var_meta    = self.host_dict[var_name]
        var_index   = var_meta["index"]
        type_code   = var_meta.get("type", 3)  # default to int32
        common_name = var_meta.get("common_name", var_name)
 
        # Normalize string values from LLM
        if isinstance(value, str):
            if value.lower() in ("true", "1"):
                value = True
            elif value.lower() in ("false", "0"):
                value = False
            else:
                try:
                    value = int(value)
                except ValueError:
                    try:
                        value = float(value)
                    except ValueError:
                        pass  # leave as string, e.g. for TYPE_CHAR
 
        # ---- DATA VALIDATION ----
        ok, error_msg = self.validate_value(var_name, type_code, value, common_name)
        if not ok:
            log("[VALIDATION_ERROR]", f"{var_name}: {error_msg}")
            self._say(error_msg, priority="critical")
            return False
 
        try:
            # ---- CHAR (0) ----
            if type_code == TYPE_CHAR:
                if not (isinstance(value, str) and len(value) == 1):
                    if isinstance(value, str) and len(value) > 1:
                        value_bytes = value.encode("utf-8")
                    else:
                        raise ValueError(f"Expected character string for {common_name}")
 
            # ---- INT8 / BOOLEAN (1) ----
            elif type_code == TYPE_INT8:
                if isinstance(value, bool) or (isinstance(value, str) and value.lower() in ("true", "false", "1", "0")):
                    if isinstance(value, str):
                        value = value.lower() in ("true", "1")
                    value_bytes = b'\x01' if value else b'\x00'
                elif isinstance(value, int):
                    value_bytes = value.to_bytes(1, "little", signed=True)
                else:
                    raise TypeError(f"Expected int8/bool for {common_name}, got {type(value).__name__}")
 
            # ---- INT16 (2) ----
            elif type_code == TYPE_INT16:
                if not isinstance(value, int):
                    raise TypeError(f"Expected int for int16, got {type(value).__name__}")
                value_bytes = value.to_bytes(2, "little", signed=True)
 
            # ---- INT32 (3) ----
            elif type_code == TYPE_INT32:
                if not isinstance(value, int):
                    raise TypeError(f"Expected int for int32, got {type(value).__name__}")
                value_bytes = value.to_bytes(4, "little", signed=True)
 
            # ---- INT64 (4) ----
            elif type_code == TYPE_INT64:
                if not isinstance(value, int):
                    raise TypeError(f"Expected int for int64, got {type(value).__name__}")
                value_bytes = value.to_bytes(8, "little", signed=True)
 
            # ---- FLOAT (5) ----
            elif type_code == TYPE_FLOAT:
                if not isinstance(value, (int, float)):
                    raise TypeError(f"Expected float for {common_name}")
                value_bytes = struct.pack("<f", float(value))
 
            # ---- DOUBLE (6) ----
            elif type_code == TYPE_DOUBLE:
                if not isinstance(value, (int, float)):
                    raise TypeError(f"Expected double for {common_name}")
                value_bytes = struct.pack("<d", float(value))
 
            # ---- POINTER (7) ----
            elif type_code == TYPE_POINTER:
                if not isinstance(value, int) or value < 0:
                    raise TypeError(f"Expected non-negative int for pointer {common_name}")
                value_bytes = value.to_bytes(8, "little", signed=False)
 
            else:
                raise ValueError(f"Unsupported type code: {type_code}")
 
        except OverflowError:
            log("[VALUE_ERROR]", f"Overflow for {common_name}: {value}")
            self._say(f"Value out of range for {common_name}: {value}", priority="critical")
            return False
 
        except (TypeError, ValueError) as e:
            log("[VALUE_ERROR]", f"{common_name}: {str(e)} (value={value})")
            self._say(f"Invalid value for {common_name}: {value}", priority="critical")
            return False

        # ---- ARRAY DIMENSION HANDLING ----
        num_dims = int(var_meta.get("num_dims", 0) or 0)
        dims = list(var_meta.get("dimensions", [])) if num_dims > 0 else []

        # Normalize indices (if any) to a list of ints
        if indices is not None:
            try:
                indices = [int(i) for i in indices]
            except Exception:
                log("[INDEX_ERROR]", f"Invalid indices for {var_name}: {indices}")
                self._say(f"Invalid index specification for {common_name}", priority="critical")
                return False

        # If this is an array variable but no indices were provided, log a warning
        # and fall back to indexing the first element only.
        index_list = []
        if num_dims > 0:
            if indices is None or len(indices) == 0:
                log("[INDEX_WARNING]", f"No indices specified for array variable {var_name}; defaulting to [0]")
                indices = [0]

            # Clamp or validate indices against declared dimensions
            for dim_idx, idx in enumerate(indices):
                max_size = dims[dim_idx] if dim_idx < len(dims) else None
                if max_size is not None and not (0 <= idx < max_size):
                    log("[INDEX_ERROR]", f"Index {idx} out of range for {var_name} dimension {dim_idx} (size {max_size})")
                    self._say(f"Index out of range for {common_name}", priority="critical")
                    return False
                index_list.append(idx)
        else:
            # Scalar variable: no indices
            index_list = []

        log("[SET_VARIABLE]", f"Set {var_name} (type_code={type_code}) to {value}")
        self._record_change(var_name, value, common_name)
        self._say(f"Set {common_name} to {value}", priority="bulk")
 
        return True
