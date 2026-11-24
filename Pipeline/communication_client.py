import socket
import struct
import threading
import time
from xmlrpc import client

from logger import log


class CommunicationClient:
    def __init__(
        self,
        host='127.0.0.1',
        port=10013,
        tts=None,
        auto_reconnect=True,
        reconnect_initial_delay=1.0,
        reconnect_max_delay=15.0,
        reconnect_backoff=2.0,
        reconnect_max_attempts=0,
        keep_alive_interval=5.0,
        status_store=None,
    ):
        self.host = host
        self.port = port
        self.sock = None  # socket will be stored here
        self.running = True
        self.tts = tts
        self.auto_reconnect = bool(auto_reconnect)
        self.reconnect_initial_delay = max(float(reconnect_initial_delay), 0.1)
        self.reconnect_max_delay = max(
            float(reconnect_max_delay), self.reconnect_initial_delay
        )
        self.reconnect_backoff = max(float(reconnect_backoff), 1.0)
        self.reconnect_max_attempts = max(int(reconnect_max_attempts), 0)
        self.status_store = status_store
        self._connected = threading.Event()
        self._connect_lock = threading.Lock()
        self._reconnect_thread = None
        self._update_page_variables = None
        self._host_dict_ref = None

         # keep-alive related variables
        self._keep_alive_thread = None
        self._keep_alive_interval = max(float(keep_alive_interval), 1.0)
        self._keep_alive_list_type = 0    
        self._keep_alive_vars = [] # variable metadata list
        # Serializes set/request so a status read cannot race the keep-alive thread.
        self._io_lock = threading.Lock()

    def _publish_status(self, **values):
        if self.status_store is None:
            return
        try:
            self.status_store.update(**values)
        except OSError as exc:
            log("[STATUS]", f"Unable to update dashboard status: {exc}")

    # ------------------------------------------------------------------
    # Low-level recv helper
    # ------------------------------------------------------------------
    def _recv_exact(self, n: int) -> bytes:
        """Receive exactly n bytes or return fewer if the socket closes.

        This mirrors the server's IOSReceive(MSG_WAITALL) behavior by
        looping until the requested number of bytes have been read or
        an error/EOF occurs.
        """
        chunks = []
        bytes_remaining = n

        while bytes_remaining > 0:
            try:
                chunk = self.sock.recv(bytes_remaining)
            except OSError as e:
                log("[COMMUNICATION]", f"ERROR: socket recv failed: {e}")
                break

            if not chunk:
                # Socket closed or no more data
                break

            chunks.append(chunk)
            bytes_remaining -= len(chunk)

        return b"".join(chunks)

    def connect(self):
        """Connect to the server and perform initialization handshake."""
        self.running = True
        if not self._connect_once():
            self._publish_status(
                server_state="disconnected",
                message="Could not connect to simulator host",
            )
            if self.tts:
                self.tts.say(
                    "Could not connect to server. Please ensure the host application is running and try again."
                )
            return False

        # Start keep-alive background thread
        if self._keep_alive_thread is None or not self._keep_alive_thread.is_alive():
            self._keep_alive_thread = threading.Thread(
                target=self._keep_alive_loop,
                name="CommClientKeepAlive",
                daemon=True,
            )
            self._keep_alive_thread.start()

        return True

    def _connect_once(self):
        """Make one connection attempt and complete the host handshake."""
        with self._connect_lock:
            if not self.running:
                return False

            new_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            new_socket.settimeout(5.0)
            try:
                new_socket.connect((self.host, self.port))
            except OSError as exc:
                log(
                    "[COMMUNICATION]",
                    f"Connection to {self.host}:{self.port} failed: {exc}",
                )
                new_socket.close()
                return False

            with self._io_lock:
                old_socket = self.sock
                self.sock = new_socket
                try:
                    if not self.send_initialization_message():
                        raise ConnectionError("initialization handshake failed")
                    self.sock.settimeout(None)
                except Exception as exc:
                    log("[COMMUNICATION]", f"Connection handshake failed: {exc}")
                    self.sock = old_socket
                    new_socket.close()
                    return False

                if old_socket is not None:
                    try:
                        old_socket.close()
                    except OSError:
                        pass
                self._connected.set()
                log("[COMMUNICATION]", f"Connected to {self.host}:{self.port}")
                self._publish_status(
                    server_state="connected",
                    server_endpoint=f"{self.host}:{self.port}",
                    message="Simulator host connected",
                )
                return True

    def _mark_disconnected(self, reason):
        """Record a lost connection and start one reconnect worker."""
        was_connected = self._connected.is_set()
        self._connected.clear()
        log("[COMMUNICATION]", f"Connection lost: {reason}")
        self._publish_status(
            server_state="reconnecting" if self.auto_reconnect else "disconnected",
            message=f"Connection lost: {reason}",
        )

        with self._io_lock:
            if self.sock is not None:
                try:
                    self.sock.close()
                except OSError:
                    pass
                self.sock = None

        if was_connected and self.tts:
            self.tts.say(
                "Simulator connection lost. Attempting to reconnect.",
                priority="critical",
            )

        if self.running and self.auto_reconnect:
            if self._reconnect_thread is None or not self._reconnect_thread.is_alive():
                self._reconnect_thread = threading.Thread(
                    target=self._reconnect_loop,
                    name="CommClientReconnect",
                    daemon=True,
                )
                self._reconnect_thread.start()

    def _reconnect_loop(self):
        delay = self.reconnect_initial_delay
        attempt = 0
        while self.running and not self._connected.is_set():
            attempt += 1
            if self.reconnect_max_attempts and attempt > self.reconnect_max_attempts:
                log("[COMMUNICATION]", "Automatic reconnect attempts exhausted")
                if self.tts:
                    self.tts.say(
                        "Unable to reconnect to the simulator.",
                        priority="critical",
                    )
                return

            log("[COMMUNICATION]", f"Reconnect attempt {attempt}")
            self._publish_status(
                server_state="reconnecting",
                message=f"Reconnect attempt {attempt}",
            )
            if self._connect_once():
                try:
                    self._restore_host_session()
                except Exception as exc:
                    self._mark_disconnected(f"session restore failed: {exc}")
                else:
                    log("[COMMUNICATION]", "Simulator connection restored")
                    self._publish_status(
                        server_state="connected",
                        message="Simulator connection restored",
                    )
                    if self.tts:
                        self.tts.say(
                            "Simulator connection restored.",
                            priority="critical",
                        )
                    return

            if self.running and not self._connected.is_set():
                time.sleep(delay)
                delay = min(delay * self.reconnect_backoff, self.reconnect_max_delay)

    def _restore_host_session(self):
        """Recreate host-side update state after a new TCP connection."""
        if not self._update_page_variables:
            return

        restored = self.create_update_page(
            self._update_page_variables,
            remember=False,
        )
        if not restored:
            raise ConnectionError("host update page could not be recreated")

        if self._host_dict_ref is not None:
            self._host_dict_ref.clear()
            self._host_dict_ref.update(restored)

        keep_alive_vars = [
            {
                "name": name,
                "index": metadata["index"],
                "type": metadata.get("type", 0),
                "num_dims": metadata.get("num_dims", 0),
                "dimensions": metadata.get("dimensions", []),
            }
            for name, metadata in restored.items()
        ]
        self.set_keep_alive_variables(keep_alive_vars, list_type=0)

    def send_initialization_message(self) -> bool:
        """Send the 16-byte initialization message and validate the ACK.

        Returns True on success, False if the ACK is invalid or not received.
        """
        int_size = struct.calcsize('i')
        header = bytes([0x49, 0x00, 0x00, 0x00])
        byte_order = struct.pack('<H', 1)          # little-endian test
        float_bytes = struct.pack('<f', 1.0)       # float test
        int_size_byte = bytes([int_size])
        spare = bytes([0x00, 0x00, 0x00, 0x00])
        trailer = bytes([0x49])
        init_msg = header + byte_order + float_bytes + int_size_byte + spare + trailer

        self.sock.sendall(init_msg)

        # The server responds with an Acknowledge message; per spec it
        # uses the same 4+len+body framing convention. We read 4 bytes
        # for header, 4 for length, then the body using _recv_exact to
        # mirror the server's MSG_WAITALL semantics.
        ack_header = self._recv_exact(4)
        if len(ack_header) != 4:
            log("[COMMUNICATION]", "ERROR: Initialization ACK header not received")
            return False

        # First byte should be the ACK message type; the remaining
        # bytes are reserved. The IOS/Host spec defines 'K' (HOST_ACK)
        # as the acknowledge message type.
        if ack_header[0] != 0x4B:  # 'K'
            log("[COMMUNICATION]", f"ERROR: Invalid ACK header during initialization: {ack_header!r}")
            return False

        ack_len_bytes = self._recv_exact(4)
        if len(ack_len_bytes) != 4:
            log("[COMMUNICATION]", "ERROR: Initialization ACK length not received")
            return False

        body_len = struct.unpack('<I', ack_len_bytes)[0]
        if body_len < 0:
            log("[COMMUNICATION]", f"ERROR: Invalid ACK body length: {body_len}")
            return False

        ack_body = self._recv_exact(body_len) if body_len > 0 else b""
        if len(ack_body) != body_len:
            log("[COMMUNICATION]", "ERROR: Incomplete ACK body received")
            return False

        # Per ICD, a zero-length ACK body indicates success; any non-zero
        # length is unusual but not fatal, so we just log it.
        if body_len != 0:
            log("[COMMUNICATION]", f"WARNING: Non-zero initialization ACK body length: {body_len}")

        return True

    def set_variable(self, list_type, var_index, value, dimensions=None):
        if not self._connected.is_set():
            raise ConnectionError("simulator is disconnected; reconnect is in progress")
        try:
            with self._io_lock:
                return self._set_variable(
                    list_type,
                    var_index,
                    value,
                    dimensions=dimensions,
                )
        except OSError as exc:
            self._mark_disconnected(exc)
            raise

    def _set_variable(self, list_type, var_index, value, dimensions=None):
        """Caller must already hold self._io_lock."""
        self._set_variable_unlocked(list_type, var_index, value, dimensions)
    
    def _set_variable_unlocked(self, list_type, var_index, value, dimensions=None):
        if dimensions is None:
            dimensions = []

        value_bytes = value if isinstance(value, bytes) else struct.pack('<i', value)

        body = struct.pack('<B', list_type)
        body += struct.pack('<I', var_index)
        body += struct.pack('<B', len(dimensions))
        for dim in dimensions:
            body += struct.pack('<I', dim)
        body += struct.pack('<I', len(value_bytes))
        body += value_bytes

        # Set Variable message header
        header = bytes([0x53, 0x00, 0x00, 0x00])  # 'S 0 0 0'
        length = struct.pack('<I', len(body))
        message = header + length + body
        self.sock.sendall(message)

        # Optionally read and log host Acknowledge ('K') if present.
        try:
            self.sock.settimeout(0.05)
            ack_header = self._recv_exact(4)
            if len(ack_header) == 4 and ack_header[0] == 0x4B:
                ack_len_bytes = self._recv_exact(4)
                if len(ack_len_bytes) == 4:
                    ack_len = struct.unpack('<I', ack_len_bytes)[0]
                    if ack_len != 0:
                        log("[COMMUNICATION]", f"Unexpected ACK length after Set Variable: {ack_len}")
        except Exception:
            # ACKs are optional; ignore timeout or socket issues here.
            pass
        finally:
            try:
                self.sock.settimeout(None)
            except Exception:
                pass

    def create_update_page(
        self,
        variables_info,
        list_type=0,
        start_index=0,
        remember=True,
    ):
        if not self._connected.is_set():
            raise ConnectionError("cannot create update page while disconnected")
        try:
            with self._io_lock:
                host_dict = self._create_update_page(
                    variables_info,
                    list_type=list_type,
                    start_index=start_index,
                )
        except OSError as exc:
            self._mark_disconnected(exc)
            raise

        if not host_dict or any("value" not in item for item in host_dict.values()):
            error = ConnectionError("host did not return a complete update page")
            self._mark_disconnected(error)
            raise error

        if remember:
            self._update_page_variables = [dict(item) for item in variables_info]
            self._host_dict_ref = host_dict
        return host_dict

    def _create_update_page(self, variables_info, list_type=0, start_index=0):
        """Create an update page based on XML-derived variable metadata.

        variables_info: list of dicts with keys at least
            "name", "type_code", "num_dims", "dimensions".

        Returns:
            host_dict mapping variable name -> dict with
                {
                    "list_type": int,
                    "index": int,
                    "type": int,
                    "num_dims": int,
                    "dimensions": list[int],
                    "value": bytes  # after first Variable Update
                }
        """
        host_dict = {}
        page_id = 0
        variables = []

        # Build local variable metadata and host_dict entries
        for i, var_info in enumerate(variables_info):
            var_index = start_index + i

            num_dims = int(var_info.get("num_dims", 0) or 0)
            dims = list(var_info.get("dimensions", [])) if num_dims > 0 else []

            variables.append({
                "index":      var_index,
                "type":       var_info["type_code"],
                "name":       var_info["name"],
                "num_dims":   num_dims,
                "dimensions": dims,
            })

            host_dict[var_info["name"]] = {
                "list_type":   list_type,
                "index":       var_index,
                "type":        var_info["type_code"],
                "num_dims":    num_dims,
                "dimensions":  dims,
                "common_name": var_info.get("common_name", var_info["name"]),
                "default":     var_info.get("default"),
                # "value" will be set once we receive the first Variable Update
            }

        # --- Send Add Update Page ---
        page_name_bytes = f"DictPage{page_id}".encode('ascii')
        body = struct.pack('<B', list_type)
        body += struct.pack('<I', page_id)
        body += struct.pack('<I', len(page_name_bytes)) + page_name_bytes
        body += struct.pack('<I', len(variables))

        for var in variables:
            body += struct.pack('<I', var["index"])
            body += struct.pack('<I', var["type"])

            # Number of array dimensions and their sizes (if any)
            num_dims = int(var.get("num_dims", 0) or 0)
            dims = list(var.get("dimensions", [])) if num_dims > 0 else []
            body += struct.pack('<B', num_dims)
            for dim_size in dims:
                body += struct.pack('<I', int(dim_size))

            name_bytes = var["name"].encode('ascii')
            body += struct.pack('<B', len(name_bytes)) + name_bytes

        header = bytes([0x50, 0x00, 0x00, 0x00])  # 'P'
        length = struct.pack('<I', len(body))
        self.sock.sendall(header + length + body)

        # --- Receive Add Update Page confirmation using exact-length reads ---
        resp_header = self._recv_exact(4)
        if len(resp_header) != 4 or resp_header[0] != 0x50:
            log("[COMMUNICATION]", "ERROR: No valid Add Update Page response from host")
            print("ERROR: No valid Add Update Page response from host")
            return host_dict

        resp_len_bytes = self._recv_exact(4)
        if len(resp_len_bytes) != 4:
            log("[COMMUNICATION]", "ERROR: Incomplete Add Update Page length from host")
            print("ERROR: Incomplete Add Update Page length from host")
            return host_dict

        body_len = struct.unpack('<I', resp_len_bytes)[0]
        body = self._recv_exact(body_len)
        if len(body) != body_len:
            log("[COMMUNICATION]", "ERROR: Incomplete Add Update Page body from host")
            print("ERROR: Incomplete Add Update Page body from host")
            return host_dict

        # Confirm message body layout per ICD:
        #   list_type (1 byte)
        #   page_id   (4 bytes)
        #   num_vars  (4 bytes)
        #   repeated num_vars times: var_index (4), status (1)
        confirm_list_type = body[0]
        confirm_page_id = struct.unpack('<I', body[1:5])[0]
        num_vars = struct.unpack('<I', body[5:9])[0]
        offset = 9

        if confirm_list_type != list_type or confirm_page_id != page_id:
            log("[COMMUNICATION]", f"WARNING: Add Update Page confirm mismatch: list_type={confirm_list_type}, page_id={confirm_page_id}")

        # Map variable indices from confirm back into our local metadata
        for i in range(num_vars):
            var_index = struct.unpack('<I', body[offset:offset+4])[0]
            offset += 4
            var_status = body[offset]
            offset += 1

            if i < len(variables):
                variables[i]["index"] = var_index
                variables[i]["status"] = var_status

        # --- Open page and request update for the newly added variables ---
        for cmd, cmd_body in [
            (0x4F, struct.pack('<B', list_type) + struct.pack('<I', page_id)),  # Open page
            (0x51, struct.pack('<B', list_type))  # Request update
        ]:
            body_len2 = struct.pack('<I', len(cmd_body))
            self.sock.sendall(bytes([cmd, 0, 0, 0]) + body_len2 + cmd_body)

        # --- Receive variable update (0x55) ---
        upd_header = self._recv_exact(4)
        if len(upd_header) != 4 or upd_header[0] != 0x55:
            log("[COMMUNICATION]", "ERROR: No variable update received from host")
            if self.tts:
                self.tts.say("ERROR: No variable update received")
            return host_dict

        upd_len_bytes = self._recv_exact(4)
        if len(upd_len_bytes) != 4:
            log("[COMMUNICATION]", "ERROR: Incomplete variable update length from host")
            if self.tts:
                self.tts.say("ERROR: Incomplete variable update length from host")
            return host_dict

        upd_body_len = struct.unpack('<I', upd_len_bytes)[0]
        body = self._recv_exact(upd_body_len)
        if len(body) != upd_body_len:
            log("[COMMUNICATION]", "ERROR: Incomplete variable update body from host")
            if self.tts:
                self.tts.say("ERROR: Incomplete variable update body from host")
            return host_dict

        num_vars = struct.unpack('<I', body[1:5])[0]
        offset = 5

        for _ in range(num_vars):
            var_index = struct.unpack('<I', body[offset:offset+4])[0]
            offset += 4
            value_size = struct.unpack('<I', body[offset:offset+4])[0]
            offset += 4
            value_bytes = body[offset:offset+value_size]
            offset += value_size

            # match var_index to variable name
            for var in variables:
                if var["index"] == var_index:
                    name = var["name"]
                    if name in host_dict:
                        host_dict[name]["value"] = value_bytes
                    else:
                        host_dict[name] = {
                            "list_type": list_type,
                            "index": var_index,
                            "type": var.get("type", 0),
                            "num_dims": var.get("num_dims", 0),
                            "dimensions": var.get("dimensions", []),
                            "value": value_bytes,
                        }
                    break

        return host_dict

    def open_update_page(self, list_type, page_id):
        """Open an existing update page."""
        header = bytes([0x4F, 0x00, 0x00, 0x00])  # 'O 0 0 0'
        body = struct.pack('<B', list_type) + struct.pack('<I', page_id)
        length = struct.pack('<I', 5)
        message = header + length + body
        self.sock.sendall(message)
 
    def close_update_page(self, list_type, page_id):
        """Close an open update page."""
        header = bytes([0x43, 0x00, 0x00, 0x00])  # 'C 0 0 0'
        body = struct.pack('<B', list_type) + struct.pack('<I', page_id)
        length = struct.pack('<I', 5)
        message = header + length + body
        self.sock.sendall(message)

    def request_update(self, list_type, variables):
        """Request an update for variables in a list and return values."""
        with self._io_lock:
            return self._request_update_unlocked(list_type, variables)
        
    def refresh_tracked_values(self):
        """Re-read keep-alive variables and return name -> metadata, including value bytes."""
        if not self._keep_alive_vars or self.sock is None:
            return {}
        return self.request_update(self._keep_alive_list_type, self._keep_alive_vars)
    
    def _request_update_unlocked(self, list_type, variables):
        """Request an update for variables in a list and return values.

        Parameters
        ----------
        list_type : int
            The IOS list type to request an update for.
        variables : list[dict]
            List of variable metadata dicts containing at least
            "index" and "name" keys. This is used to map indices in the
            update message back to variable names.

        Returns
        -------
        dict
            Mapping variable name -> {"list_type", "index", "value"}.
        """
        header = bytes([0x51, 0x00, 0x00, 0x00])  # 'Q 0 0 0'
        body = struct.pack('<B', list_type)
        length = struct.pack('<I', len(body))
        message = header + length + body
        self.sock.sendall(message)

        update_dict = {}

        # --- Receive variable update (0x55) ---
        upd_header = self._recv_exact(4)
        if len(upd_header) != 4 or upd_header[0] != 0x55:
            log("[COMMUNICATION]", "ERROR: No variable update received from host in request_update")
            if self.tts:
                self.tts.say("ERROR: No variable update received")
            return update_dict

        upd_len_bytes = self._recv_exact(4)
        if len(upd_len_bytes) != 4:
            log("[COMMUNICATION]", "ERROR: Incomplete variable update length from host in request_update")
            if self.tts:
                self.tts.say("ERROR: Incomplete variable update length from host")
            return update_dict

        upd_body_len = struct.unpack('<I', upd_len_bytes)[0]
        body = self._recv_exact(upd_body_len)
        if len(body) != upd_body_len:
            log("[COMMUNICATION]", "ERROR: Incomplete variable update body from host in request_update")
            if self.tts:
                self.tts.say("ERROR: Incomplete variable update body from host")
            return update_dict

        # Body layout:
        #   list_type (1 byte)
        #   num_vars  (4 bytes)
        #   repeated num_vars times:
        #       var_index (4)
        #       value_size (4)
        #       value_bytes (value_size)
        msg_list_type = body[0]
        num_vars = struct.unpack('<I', body[1:5])[0]
        offset = 5

        if msg_list_type != list_type:
            log("[COMMUNICATION]", f"WARNING: Variable update list_type mismatch: expected {list_type}, got {msg_list_type}")

        for _ in range(num_vars):
            var_index = struct.unpack('<I', body[offset:offset+4])[0]
            offset += 4
            value_size = struct.unpack('<I', body[offset:offset+4])[0]
            offset += 4
            value_bytes = body[offset:offset+value_size]
            offset += value_size

            # match var_index to variable name
            for var in variables:
                if var["index"] == var_index:
                    name = var.get("name", f"IDX_{var_index}")
                    update_dict[name] = {
                        "list_type": list_type,
                        "index": var_index,
                        "type": var.get("type", 0),
                        "num_dims": var.get("num_dims", 0),
                        "dimensions": var.get("dimensions", []),
                        "value": value_bytes,
                    }
                    break

        return update_dict

    # ------------------------------------------------------------------
    # Keep-alive methods
    # ------------------------------------------------------------------
    def set_keep_alive_variables(self, variables_info, list_type=0):
        """
        Configure which variables to use in periodic request_update calls.
        variables_info should be a list of dicts with at least 'index' and 'name'.
        """
        self._keep_alive_list_type = list_type
        # Only keep the fields request_update uses
        self._keep_alive_vars = [
            {
                "index": v["index"],
                "name": v["name"],
                "type": v.get("type_code", v.get("type", 0)),
                "num_dims": v.get("num_dims", 0),
                "dimensions": v.get("dimensions", []),
            }
            for v in variables_info
        ]

    def keep_alive(self):
        """Keep connection alive until disconnected; automatically exit on disconnect."""
        try:
            self.sock.settimeout(1.0)
            while self.running:
                try:
                    data = self.sock.recv(1024)
                    if not data:
                        if self.running:
                            self.running = False
                            self.tts.say("ERROR: Server disconnected.")
                            log("[COMMUNICATION]", "ERROR: Server disconnected.")
                        break
                except socket.timeout:
                    continue 
                except socket.error:
                    if self.running:
                        self.running = False
                        self.tts.say("ERROR: Socket error, disconnecting.")
                        log("[COMMUNICATION]", "ERROR: Socket error")
                    break
                time.sleep(0.1)
        finally:
            self.exit()
            import os
            os._exit(0)
            
    def _keep_alive_loop(self):
        """Periodically send Request Update messages to keep the TCP connection alive."""
        while self.running:
            if not self._connected.is_set():
                time.sleep(0.25)
                continue
            try:
                if self.sock is None:
                    self._mark_disconnected("socket is unavailable")
                    continue
                if self._keep_alive_vars:
                    self.request_update(self._keep_alive_list_type, self._keep_alive_vars)
            except OSError as e:
                log("[COMMUNICATION]", f"ERROR in keep-alive loop: {e}")
                if self._connected.is_set():
                    self._mark_disconnected(e)
            except Exception as e:
                log("[COMMUNICATION]", f"Keep-alive exception: {e}")
            time.sleep(self._keep_alive_interval)

    def exit(self):
        """Send Exit Message to terminate connection."""
        self.running = False
        self._connected.clear()
        self._publish_status(
            server_state="disconnected",
            merlin_state="offline",
            message="Merlin stopped",
        )

        if self.sock:
            try:
                header = bytes([0x45, 0x00, 0x00, 0x00])
                length = struct.pack('<I', 0)
                message = header + length
                self.sock.sendall(message)
            except Exception:
                pass
            finally:
                try:
                    self.sock.close()
                except Exception:
                    pass
    def create_update_page_simple(self, variable_names, list_type=0):
        """Create an update page using only variable names.

        This helper mirrors `create_update_page` but assumes scalar
        variables (no array dimensions) and uses exact-length reads
        for all protocol messages.
        """
        host_dict = {}
        page_id = 1
        variables = [{"index": 0, "type": 0, "name": name, "num_dims": 0, "dimensions": []}
                     for name in variable_names]

        # --- Send Add Update Page ---
        page_name_bytes = f"DictPage{page_id}".encode('ascii')
        body = struct.pack('<B', list_type) + struct.pack('<I', page_id)
        body += struct.pack('<I', len(page_name_bytes)) + page_name_bytes
        body += struct.pack('<I', len(variables))

        for var in variables:
            body += struct.pack('<I', var["index"]) + struct.pack('<I', var["type"])
            body += struct.pack('<B', 0)  # num dimensions = 0 for simple case
            name_bytes = var["name"].encode('ascii')
            body += struct.pack('<B', len(name_bytes)) + name_bytes

        header = bytes([0x50, 0x00, 0x00, 0x00])
        length = struct.pack('<I', len(body))
        self.sock.sendall(header + length + body)

        # --- Receive confirmation ---
        resp_header = self._recv_exact(4)
        if len(resp_header) != 4 or resp_header[0] != 0x50:
            log("[COMMUNICATION]", "ERROR: No valid Add Update Page response from host")
            print("ERROR: No valid Add Update Page response from host")
            return host_dict

        resp_len_bytes = self._recv_exact(4)
        if len(resp_len_bytes) != 4:
            log("[COMMUNICATION]", "ERROR: Incomplete Add Update Page length from host")
            print("ERROR: Incomplete Add Update Page length from host")
            return host_dict

        body_len = struct.unpack('<I', resp_len_bytes)[0]
        body = self._recv_exact(body_len)
        if len(body) != body_len:
            log("[COMMUNICATION]", "ERROR: Incomplete Add Update Page body from host")
            print("ERROR: Incomplete Add Update Page body from host")
            return host_dict

        num_vars = struct.unpack('<I', body[5:9])[0]
        offset = 9
        for i in range(num_vars):
            var_index = struct.unpack('<I', body[offset:offset+4])[0]
            offset += 4
            var_status = body[offset]
            offset += 1
            if i < len(variables):
                variables[i]["index"] = var_index
                variables[i]["status"] = var_status

        # --- Open page and request update ---
        for cmd, cmd_body in [
            (0x4F, struct.pack('<B', list_type) + struct.pack('<I', page_id)),  # Open page
            (0x51, struct.pack('<B', list_type))  # Request update
        ]:
            body_len2 = struct.pack('<I', len(cmd_body))
            self.sock.sendall(bytes([cmd, 0, 0, 0]) + body_len2 + cmd_body)

        # --- Receive variable update (0x55) ---
        upd_header = self._recv_exact(4)
        if len(upd_header) != 4 or upd_header[0] != 0x55:
            log("[COMMUNICATION]", "ERROR: No variable update received from host")
            if self.tts:
                self.tts.say("ERROR: No variable update received")
            return host_dict

        upd_len_bytes = self._recv_exact(4)
        if len(upd_len_bytes) != 4:
            log("[COMMUNICATION]", "ERROR: Incomplete variable update length from host")
            if self.tts:
                self.tts.say("ERROR: Incomplete variable update length from host")
            return host_dict

        upd_body_len = struct.unpack('<I', upd_len_bytes)[0]
        body = self._recv_exact(upd_body_len)
        if len(body) != upd_body_len:
            log("[COMMUNICATION]", "ERROR: Incomplete variable update body from host")
            if self.tts:
                self.tts.say("ERROR: Incomplete variable update body from host")
            return host_dict

        num_vars = struct.unpack('<I', body[1:5])[0]
        offset = 5

        for _ in range(num_vars):
            var_index = struct.unpack('<I', body[offset:offset+4])[0]
            offset += 4
            value_size = struct.unpack('<I', body[offset:offset+4])[0]
            offset += 4
            value_bytes = body[offset:offset+value_size]
            offset += value_size

            # match var_index to variable name
            for var in variables:
                if var["index"] == var_index:
                    host_dict[var["name"]] = {
                        "list_type": list_type,
                        "index": var_index,
                        "type": var.get("type", 0),
                        "num_dims": var.get("num_dims", 0),
                        "dimensions": var.get("dimensions", []),
                        "value": value_bytes,
                    }
                    break

        return host_dict
        length = struct.unpack('<I', data[4:8])[0]
        body = data[8:8+length]
        num_vars = struct.unpack('<I', body[1:5])[0]
        offset = 5

        for _ in range(num_vars):
            var_index = struct.unpack('<I', body[offset:offset+4])[0]
            offset += 4
            value_size = struct.unpack('<I', body[offset:offset+4])[0]
            offset += 4
            value_bytes = body[offset:offset+value_size]
            offset += value_size

            # match var_index to variable name
            for var in variables:
                if var["index"] == var_index:
                    host_dict[var["name"]] = {
                        "list_type": list_type,
                        "index": var_index,
                        "type": var.get("type", 0),
                        "value": value_bytes
                    }
                    break

        return host_dict

    

