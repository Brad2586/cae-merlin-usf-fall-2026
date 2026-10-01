using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;
using System.Windows.Forms;

namespace DataSetGenerator
{
    public partial class DataSetGeneration : Form
    {
        // =========================
        // Global variables for max random variants
        // =========================
        private int maxRandomVariantsSingle = 10;
        private int maxRandomVariantsMulti = 10;
        private int maxFloatDoubleLines = 5;
        private readonly Random _random = new Random();

        // =========================
        // Generation mode (strict / lenient)
        // =========================
        private enum GenerationMode { Strict, Lenient }
        private GenerationMode _generationMode = GenerationMode.Strict;

        /// <summary>
        /// Returns the input phrases for the current mode.
        /// Always includes "default" phrases. Adds "strict" phrases only in Strict mode,
        /// "lenient" phrases only in Lenient mode.
        /// </summary>
        private List<string> GetModeFilteredInputs(List<string> @default, List<string> strict, List<string> lenient)
        {
            var result = new List<string>();
            if (@default != null) result.AddRange(@default);
            if (_generationMode == GenerationMode.Strict && strict != null) result.AddRange(strict);
            if (_generationMode == GenerationMode.Lenient && lenient != null) result.AddRange(lenient);
            return result;
        }

        string filePath = @"C:\Users\zaguirre\.vscode\test-repo\DataSet\DataSetGenerator\dataset.jsonl";
        // // Path where dataset.jsonl will be saved
        // private readonly string filePath =
        //     Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "dataset.jsonl");

        // =========================
        // Models
        // =========================
        public class OutputData
        {
            public string Type { get; set; }

            [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
            public List<string> parameters_keys { get; set; }

            [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
            public List<string> parameters_values { get; set; }

            [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
            public string message { get; set; }
        }

        public class DataPoint
        {
            public string input { get; set; }
            public OutputData output { get; set; }
        }

        public class Parameter
        {
            public string key { get; set; }
            public string @default { get; set; }
        }

        public class DefaultEntry
        {
            public string key { get; set; }
            public string value { get; set; }
            public string type { get; set; }
            public List<string> input { get; set; }
            public string message { get; set; }

            [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
            public List<string> excluded_keys { get; set; }
        }

        public class CommandTypedEntry
        {
            public string key { get; set; }
            public string value { get; set; }
            public List<string> input { get; set; }
        }

        public class MultiKeyEntry
        {
            public List<string> keys { get; set; }
            public List<string> values { get; set; }
            public List<string> input { get; set; }
        }

        public class MultiClarificationEntry
        {
            public string message { get; set; }
            public List<string> keys { get; set; }
            public List<string> values { get; set; }
            public List<string> input { get; set; }
        }

        public class AllowedEntry
        {
            public string key { get; set; }
            public string value { get; set; }
            public List<string> input { get; set; }
        }

        public class MultiClarificationAllowedEntry
        {
            public string message { get; set; }
            public List<string> keys { get; set; }
            public List<string> values { get; set; }
            public List<string> input { get; set; }
            public List<AllowedEntry> allowed { get; set; }
        }

        public class ApproachEntry
        {
            public List<string> keys { get; set; }
            public List<string> values { get; set; }
            public List<string> input { get; set; }
        }

        public class MultiLevelErrorEntry
        {
            public string message { get; set; }
        }

        public class ParameterConfig
        {
            public List<Parameter> parameters { get; set; }
            public List<string> type { get; set; }
            public List<string> messages { get; set; }

            [JsonPropertyName("single_default")]
            public JsonElement single_default { get; set; }

            [JsonPropertyName("multi_default")]
            public JsonElement multi_default { get; set; }
        }

        public class VariationConfigExtended
        {
            public Dictionary<string, List<string>> variations { get; set; }
            public Dictionary<string, List<string>> @char { get; set; }
            public Dictionary<string, List<double>> @float { get; set; }
            public Dictionary<string, List<double>> @double { get; set; }
        }

        private List<DataPoint> dataPoints = new List<DataPoint>();
        private ParameterConfig config;
        private VariationConfigExtended variationConfig;

        private List<DefaultEntry> _commandBoolDefaults;
        private List<DefaultEntry> _commandBoolStrict;
        private List<DefaultEntry> _commandBoolLenient;
        private List<DefaultEntry> _clarificationResponseDefaults;
        private List<CommandTypedEntry> _commandCharDefaults;
        private List<CommandTypedEntry> _commandFloatDefaults;
        private List<CommandTypedEntry> _commandDoubleDefaults;
        private List<DefaultEntry> _clarificationDefaults;
        private List<string> _errorDefaultPhrases;
        private List<string> _errorStrictPhrases;
        private string _errorMessage;
        private List<DefaultEntry> _exitDefaults;
        private List<DefaultEntry> _exitLenient;
        private List<DefaultEntry> _modeDefaults;
        private List<MultiKeyEntry> _allEngineDefault;
        private List<MultiKeyEntry> _allEngineLenient;
        private List<ApproachEntry> _approachEntries;
        private string _multiLevelErrorMessage;
        private List<MultiClarificationEntry> _multiClarificationDefaults;
        private List<MultiClarificationAllowedEntry> _multiClarificationAllowed;

        public DataSetGeneration()
        {
            InitializeComponent();

            SetupGridFix();

            radioButton_Single.Checked = true;

            LoadParameters();
            LoadVariations();
            UpdateModeUI();

            radioButton_Single.CheckedChanged += ModeChanged;
            radioButton_Multi.CheckedChanged += ModeChanged;
            button_GenerateLines.Click += button_GenerateLines_Click;
            button_Restart.Click += button_Restart_Click;
            comboBox_Type.SelectedIndexChanged += TypeChanged;

            checkBox_NumberExpansion.Checked = true;
            checkBox_Variations.Checked = true;

            checkBox_GenSingleCommand.Checked = true;
            checkBox_GenClarification.Checked = true;
            checkBox_GenExtraTypes.Checked = true;
            checkBox_GenMultiCommand.Checked = true;
            checkBox_GenMultiDefaults.Checked = true;
            checkBox_GenMultiLevelClarification.Checked = true;
            checkBox_GenMultiLevelValueErrors.Checked = true;
            checkBox_GenMultiLevelErrors.Checked = true;
            checkBox_GenApproach.Checked = true;

            comboBox_VariantCountSingle.Items.AddRange(new object[] { 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 });
            comboBox_VariantCountSingle.SelectedItem = maxRandomVariantsSingle;
            comboBox_VariantCountSingle.SelectedIndexChanged += MaxVariantsSingleChanged;

            comboBox_VariantCountMulti.Items.AddRange(new object[] { 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 });
            comboBox_VariantCountMulti.SelectedItem = maxRandomVariantsMulti;
            comboBox_VariantCountMulti.SelectedIndexChanged += MaxVariantsMultiChanged;

            comboBox_VariantCountFloatDouble.Items.AddRange(new object[] { 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 });
            comboBox_VariantCountFloatDouble.SelectedItem = maxFloatDoubleLines;
            comboBox_VariantCountFloatDouble.SelectedIndexChanged += MaxVariantsFloatDoubleChanged;

            radioButton_ModeStrict.Checked = true;
            radioButton_ModeStrict.CheckedChanged += GenerationModeChanged;
            radioButton_ModeLenient.CheckedChanged += GenerationModeChanged;
        }

        private void GenerationModeChanged(object sender, EventArgs e)
        {
            _generationMode = radioButton_ModeStrict.Checked
                ? GenerationMode.Strict
                : GenerationMode.Lenient;
        }

        private void MaxVariantsSingleChanged(object sender, EventArgs e)
        {
            if (comboBox_VariantCountSingle.SelectedItem != null)
                maxRandomVariantsSingle = Convert.ToInt32(comboBox_VariantCountSingle.SelectedItem);
        }

        private void MaxVariantsMultiChanged(object sender, EventArgs e)
        {
            if (comboBox_VariantCountMulti.SelectedItem != null)
                maxRandomVariantsMulti = Convert.ToInt32(comboBox_VariantCountMulti.SelectedItem);
        }

        private void MaxVariantsFloatDoubleChanged(object sender, EventArgs e)
        {
            if (comboBox_VariantCountFloatDouble.SelectedItem != null)
                maxFloatDoubleLines = Convert.ToInt32(comboBox_VariantCountFloatDouble.SelectedItem);
        }

        private void SetupGridFix()
        {
            dataGridView_Multi.Columns.Clear();

            var keyCol = new DataGridViewTextBoxColumn();
            keyCol.Name = "ParameterKey";
            keyCol.HeaderText = "Parameter Key";
            keyCol.ReadOnly = true;

            var valueCol = new DataGridViewComboBoxColumn();
            valueCol.Name = "Value";
            valueCol.HeaderText = "Value";
            valueCol.Items.AddRange("true", "false");

            dataGridView_Multi.Columns.Add(keyCol);
            dataGridView_Multi.Columns.Add(valueCol);

            dataGridView_Multi.AllowUserToAddRows = false;
        }

        // =========================
        // Loading
        // =========================

        private void LoadParameters()
        {
            try
            {
                string json = File.ReadAllText("parameters.json");
                var options = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };
                config = JsonSerializer.Deserialize<ParameterConfig>(json, options);

                ParseDefaults();

                PopulateSingleCombo();
                PopulateMultiGrid();
                PopulateTypeDropdown();
                PopulateMessagesDropdown();
            }
            catch (Exception ex)
            {
                MessageBox.Show("Error loading parameters.json:\n" + ex.Message);
            }
        }

        private void ParseDefaults()
        {
            _multiClarificationAllowed = new List<MultiClarificationAllowedEntry>();
            _commandBoolDefaults = new List<DefaultEntry>();
            _commandBoolStrict = new List<DefaultEntry>();
            _commandBoolLenient = new List<DefaultEntry>();
            _clarificationResponseDefaults = new List<DefaultEntry>();
            _commandCharDefaults = new List<CommandTypedEntry>();
            _commandFloatDefaults = new List<CommandTypedEntry>();
            _commandDoubleDefaults = new List<CommandTypedEntry>();
            _clarificationDefaults = new List<DefaultEntry>();
            _errorDefaultPhrases = new List<string>();
            _errorStrictPhrases = new List<string>();
            _errorMessage = "error, command not recognized";
            _exitDefaults = new List<DefaultEntry>();
            _exitLenient = new List<DefaultEntry>();
            _modeDefaults = new List<DefaultEntry>();
            _allEngineDefault = new List<MultiKeyEntry>();
            _allEngineLenient = new List<MultiKeyEntry>();
            _approachEntries = new List<ApproachEntry>();
            _multiLevelErrorMessage = "multiple missing values, please try again";
            _multiClarificationDefaults = new List<MultiClarificationEntry>();

            var opts = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };

            if (config.single_default.ValueKind == JsonValueKind.Object)
            {
                var sd = config.single_default;

                if (sd.TryGetProperty("command_boolean", out var cb) && cb.ValueKind == JsonValueKind.Object)
                {
                    _commandBoolDefaults = DeserializeArrayProp<DefaultEntry>(cb, "default", opts);
                    _commandBoolStrict = DeserializeArrayProp<DefaultEntry>(cb, "strict", opts);
                    _commandBoolLenient = DeserializeArrayProp<DefaultEntry>(cb, "lenient", opts);
                    _clarificationResponseDefaults = DeserializeArrayProp<DefaultEntry>(cb, "clarification_response", opts);
                }

                if (sd.TryGetProperty("command_char", out var cc) && cc.ValueKind == JsonValueKind.Object)
                    _commandCharDefaults = DeserializeArrayProp<CommandTypedEntry>(cc, "default", opts);

                if (sd.TryGetProperty("command_float", out var cf) && cf.ValueKind == JsonValueKind.Object)
                    _commandFloatDefaults = DeserializeArrayProp<CommandTypedEntry>(cf, "default", opts);

                if (sd.TryGetProperty("command_double", out var cd) && cd.ValueKind == JsonValueKind.Object)
                    _commandDoubleDefaults = DeserializeArrayProp<CommandTypedEntry>(cd, "default", opts);

                if (sd.TryGetProperty("clarification", out var clar) && clar.ValueKind == JsonValueKind.Object)
                    _clarificationDefaults = DeserializeArrayProp<DefaultEntry>(clar, "default", opts);

                if (sd.TryGetProperty("error", out var errEl) && errEl.ValueKind == JsonValueKind.Object)
                {
                    if (errEl.TryGetProperty("message", out var msgEl))
                        _errorMessage = msgEl.GetString();

                    _errorDefaultPhrases = FlattenInputArrays(errEl, "default");
                    _errorStrictPhrases = FlattenInputArrays(errEl, "strict");
                }

                if (sd.TryGetProperty("exit", out var exitEl) && exitEl.ValueKind == JsonValueKind.Object)
                {
                    _exitDefaults = DeserializeArrayProp<DefaultEntry>(exitEl, "default", opts);
                    _exitLenient = DeserializeArrayProp<DefaultEntry>(exitEl, "lenient", opts);
                }

                if (sd.TryGetProperty("mode", out var modeEl) && modeEl.ValueKind == JsonValueKind.Object)
                    _modeDefaults = DeserializeArrayProp<DefaultEntry>(modeEl, "default", opts);
            }

            if (config.multi_default.ValueKind == JsonValueKind.Object)
            {
                var md = config.multi_default;

                if (md.TryGetProperty("all_engine", out var ae) && ae.ValueKind == JsonValueKind.Object)
                {
                    _allEngineDefault = DeserializeArrayProp<MultiKeyEntry>(ae, "default", opts);
                    _allEngineLenient = DeserializeArrayProp<MultiKeyEntry>(ae, "lenient", opts);
                }

                if (md.TryGetProperty("approach", out var appr) && appr.ValueKind == JsonValueKind.Array)
                    _approachEntries = JsonSerializer.Deserialize<List<ApproachEntry>>(appr.GetRawText(), opts);

                if (md.TryGetProperty("error", out var mErr) && mErr.ValueKind == JsonValueKind.Object)
                {
                    var entries = DeserializeArrayProp<MultiLevelErrorEntry>(mErr, "default", opts);
                    if (entries?.Count > 0 && entries[0].message != null)
                        _multiLevelErrorMessage = entries[0].message;
                }

                if (md.TryGetProperty("clarification", out var mClar) && mClar.ValueKind == JsonValueKind.Object)
                {
                    _multiClarificationDefaults = DeserializeArrayProp<MultiClarificationEntry>(mClar, "default", opts);
                    _multiClarificationAllowed = DeserializeArrayProp<MultiClarificationAllowedEntry>(mClar, "default", opts);
                    _multiClarificationAllowed = _multiClarificationAllowed
                        .Where(e => e.allowed != null && e.allowed.Count > 0)
                        .ToList();
                }
            }
        }

        private List<T> DeserializeArrayProp<T>(JsonElement parent, string propName, JsonSerializerOptions opts)
        {
            if (parent.TryGetProperty(propName, out var el) && el.ValueKind == JsonValueKind.Array)
                return JsonSerializer.Deserialize<List<T>>(el.GetRawText(), opts) ?? new List<T>();
            return new List<T>();
        }

        private List<string> FlattenInputArrays(JsonElement parent, string propName)
        {
            var result = new List<string>();
            if (!parent.TryGetProperty(propName, out var arr) || arr.ValueKind != JsonValueKind.Array)
                return result;

            foreach (var item in arr.EnumerateArray())
            {
                if (item.TryGetProperty("input", out var inputArr) && inputArr.ValueKind == JsonValueKind.Array)
                    foreach (var phrase in inputArr.EnumerateArray())
                        if (phrase.ValueKind == JsonValueKind.String)
                            result.Add(phrase.GetString());
            }
            return result;
        }

        private List<DefaultEntry> GetCurrentBoolCommandEntries()
        {
            var result = new List<DefaultEntry>(_commandBoolDefaults);
            if (_generationMode == GenerationMode.Strict)
                result.AddRange(_commandBoolStrict);
            else
                result.AddRange(_commandBoolLenient);
            return result;
        }

        private List<MultiKeyEntry> GetCurrentAllEngineEntries()
        {
            var result = new List<MultiKeyEntry>(_allEngineDefault);
            if (_generationMode == GenerationMode.Lenient)
                result.AddRange(_allEngineLenient);
            return result;
        }

        private void LoadVariations()
        {
            try
            {
                string json = File.ReadAllText("variations.json");
                variationConfig = JsonSerializer.Deserialize<VariationConfigExtended>(json);
            }
            catch
            {
                variationConfig = new VariationConfigExtended
                {
                    variations = new Dictionary<string, List<string>>(),
                    @char = new Dictionary<string, List<string>>(),
                    @float = new Dictionary<string, List<double>>(),
                    @double = new Dictionary<string, List<double>>()
                };
            }
        }

        private void PopulateTypeDropdown()
        {
            comboBox_Type.Items.Clear();
            foreach (var t in config.type)
                comboBox_Type.Items.Add(t);
            if (comboBox_Type.Items.Count > 0)
                comboBox_Type.SelectedIndex = 0;

            UpdateMessageUI();
        }

        private void PopulateMessagesDropdown()
        {
            if (config.messages == null) return;

            comboBox_Message.Items.Clear();
            foreach (var m in config.messages)
                comboBox_Message.Items.Add(m);
            if (comboBox_Message.Items.Count > 0)
                comboBox_Message.SelectedIndex = 0;
        }

        private void PopulateSingleCombo()
        {
            comboBox_SingleParameterKey.Items.Clear();
            foreach (var p in config.parameters)
                comboBox_SingleParameterKey.Items.Add(p.key);

            comboBox_ParameterValueSingle.SelectedIndex = 0;
        }

        private void PopulateMultiGrid()
        {
            dataGridView_Multi.Rows.Clear();
            foreach (var p in config.parameters)
                dataGridView_Multi.Rows.Add(p.key, p.@default);
        }

        private void ModeChanged(object sender, EventArgs e) => UpdateModeUI();

        private void UpdateModeUI()
        {
            bool isSingle = radioButton_Single.Checked;
            groupBox_SingleCommand.Visible = isSingle;
            groupBox_MultiCommand.Visible = !isSingle;
        }

        private void TypeChanged(object sender, EventArgs e) => UpdateMessageUI();

        private void UpdateMessageUI()
        {
            string selected = comboBox_Type.SelectedItem?.ToString();
            bool messageEnabled = selected == "clarification" || selected == "error";
            bool parametersEnabled = selected == "command" || selected == "mode";

            comboBox_Message.Enabled = messageEnabled;
            label_Message.Enabled = messageEnabled;

            comboBox_SingleParameterKey.Enabled = parametersEnabled;
            comboBox_ParameterValueSingle.Enabled = parametersEnabled;
        }

        // =========================
        // Variation Helpers
        // =========================

        private List<(string original, List<string> options)> TokenizeWithVariations(string input)
        {
            var sortedKeys = variationConfig.variations.Keys
                .OrderByDescending(k => k.Split(' ').Length)
                .ThenByDescending(k => k.Length)
                .ToList();

            var segments = new List<(string original, List<string> options)>();
            int i = 0;
            string lower = input.ToLower();

            while (i < input.Length)
            {
                bool matched = false;

                foreach (var key in sortedKeys)
                {
                    if (i + key.Length > lower.Length) continue;

                    string slice = lower.Substring(i, key.Length);
                    if (slice != key.ToLower()) continue;

                    bool startOk = i == 0 || !char.IsLetterOrDigit(lower[i - 1]);
                    bool endOk = i + key.Length == lower.Length || !char.IsLetterOrDigit(lower[i + key.Length]);
                    if (!startOk || !endOk) continue;

                    string originalSlice = input.Substring(i, key.Length);
                    segments.Add((originalSlice, variationConfig.variations[key]));
                    i += key.Length;
                    matched = true;
                    break;
                }

                if (!matched)
                {
                    if (segments.Count > 0 && segments[segments.Count - 1].options == null)
                    {
                        var last = segments[segments.Count - 1];
                        segments[segments.Count - 1] = (last.original + input[i], null);
                    }
                    else
                    {
                        segments.Add((input[i].ToString(), null));
                    }
                    i++;
                }
            }

            return segments;
        }

        private List<string> GenerateRandomVariants(string input, int maxCount, HashSet<string> onlyVaryTheseKeys = null)
        {
            var segments = TokenizeWithVariations(input);

            var replaceableIndices = segments
                .Select((s, idx) => (s, idx))
                .Where(x =>
                {
                    if (x.s.options == null || x.s.options.Count <= 1) return false;
                    if (onlyVaryTheseKeys == null) return true;
                    return onlyVaryTheseKeys.Contains(x.s.original.ToLower().Trim());
                })
                .Select(x => x.idx)
                .ToList();

            if (replaceableIndices.Count == 0)
                return new List<string> { input };

            // Always include the original phrase first
            var variants = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { input };

            int attempts = 0;
            int maxAttempts = maxCount * 30;

            while (variants.Count <= maxCount && attempts < maxAttempts)
            {
                attempts++;

                var sb = new StringBuilder();

                for (int i = 0; i < segments.Count; i++)
                {
                    var (original, options) = segments[i];

                    if (replaceableIndices.Contains(i) && options != null)
                    {
                        // Independently randomize every replaceable slot on every attempt
                        sb.Append(options[_random.Next(options.Count)]);
                    }
                    else
                    {
                        sb.Append(original);
                    }
                }

                variants.Add(sb.ToString());
            }

            var results = variants.ToList();
            return results.Count > maxCount + 1
                ? results.Take(maxCount + 1).ToList()
                : results;
        }

        private List<string> GetVariants(string inputPhrase, int maxCount)
        {
            if (!checkBox_Variations.Checked)
                return new List<string> { inputPhrase };

            return GenerateRandomVariants(inputPhrase, maxCount);
        }

        // =========================
        // Cartesian / Combinations
        // =========================
        private IEnumerable<List<T>> GetCombinations<T>(List<T> list, int size)
        {
            if (size == 0) { yield return new List<T>(); yield break; }

            for (int i = 0; i <= list.Count - size; i++)
            {
                foreach (var rest in GetCombinations(list.Skip(i + 1).ToList(), size - 1))
                {
                    var combo = new List<T> { list[i] };
                    combo.AddRange(rest);
                    yield return combo;
                }
            }
        }

        // =========================
        // Generate Defaults
        // =========================
        private void button_Defaults_Click(object sender, EventArgs e)
        {
            if (config == null) return;

            var newPoints = new List<DataPoint>();

            if (checkBox_GenSingleCommand.Checked)
                GenerateSingleCommandDefaults(newPoints);

            if (checkBox_GenClarification.Checked)
                GenerateClarificationDefaults(newPoints);

            if (checkBox_GenExtraTypes.Checked)
                GenerateExtraTypeDefaults(newPoints);

            if (checkBox_GenMultiCommand.Checked)
                GenerateMultiCommandCombinations(newPoints);

            if (checkBox_GenMultiDefaults.Checked)
                GenerateMultiDefaultsCombinations(newPoints);

            if (checkBox_GenMultiLevelClarification.Checked)
                GenerateMultiLevelClarification(newPoints);

            if (checkBox_GenMultiLevelValueErrors.Checked)
                GenerateMultiLevelValueErrors(newPoints);

            if (checkBox_GenMultiLevelErrors.Checked)
                GenerateMultiLevelErrors(newPoints);

            if (checkBox_GenApproach.Checked)
                GenerateApproachDefaults(newPoints);

            GenerateMultiDefaultAllowedClarifications(newPoints);

            newPoints = newPoints
                .Where(dp => !string.IsNullOrWhiteSpace(dp.input))
                .GroupBy(dp => dp.input.ToLower().Trim())
                .Select(g => g.First())
                .ToList();

            SaveToJsonl(newPoints);
        }

        // ---- 1. Single command defaults ----
        private void GenerateSingleCommandDefaults(List<DataPoint> newPoints)
        {
            // Boolean commands — vary ALL tokens independently
            foreach (var entry in GetCurrentBoolCommandEntries())
            {
                if (entry.input == null) continue;

                foreach (var inputPhrase in entry.input)
                {
                    var variants = GetVariants(inputPhrase, maxRandomVariantsSingle);

                    foreach (var v in variants)
                    {
                        newPoints.Add(new DataPoint
                        {
                            input = v,
                            output = new OutputData
                            {
                                Type = "command",
                                parameters_keys = new List<string> { entry.key },
                                parameters_values = new List<string> { entry.value }
                            }
                        });
                    }
                }
            }

            // all_engine multi-key commands — vary ALL tokens independently
            foreach (var entry in GetCurrentAllEngineEntries())
            {
                if (entry.input == null) continue;

                foreach (var inputPhrase in entry.input)
                {
                    var variants = GetVariants(inputPhrase, maxRandomVariantsSingle);

                    foreach (var v in variants)
                    {
                        newPoints.Add(new DataPoint
                        {
                            input = v,
                            output = new OutputData
                            {
                                Type = "command",
                                parameters_keys = new List<string>(entry.keys),
                                parameters_values = new List<string>(entry.values)
                            }
                        });
                    }
                }
            }

            GenerateCharCommandDefaults(newPoints);
            GenerateFloatCommandDefaults(newPoints);
            GenerateDoubleCommandDefaults(newPoints);
            GenerateClarificationResponseDefaults(newPoints);
        }

        // ---- 1b. clarification_response defaults ----
        private void GenerateClarificationResponseDefaults(List<DataPoint> newPoints)
        {
            foreach (var entry in _clarificationResponseDefaults)
            {
                if (entry.input == null) continue;

                foreach (var inputPhrase in entry.input)
                {
                    int questionMarkIdx = inputPhrase.IndexOf('?');

                    if (questionMarkIdx >= 0 && questionMarkIdx < inputPhrase.Length - 1)
                    {
                        // Lock the prefix (before and including '?'), only vary the suffix
                        string prefix = inputPhrase.Substring(0, questionMarkIdx + 1);
                        string suffix = inputPhrase.Substring(questionMarkIdx + 1).Trim();

                        var suffixVariants = GetVariants(suffix, maxRandomVariantsSingle);

                        foreach (var variedSuffix in suffixVariants)
                        {
                            newPoints.Add(new DataPoint
                            {
                                input = $"{prefix} {variedSuffix}",
                                output = new OutputData
                                {
                                    Type = "command",
                                    parameters_keys = new List<string> { entry.key },
                                    parameters_values = new List<string> { entry.value }
                                }
                            });
                        }
                    }
                    else
                    {
                        var variants = GetVariants(inputPhrase, maxRandomVariantsSingle);

                        foreach (var v in variants)
                        {
                            newPoints.Add(new DataPoint
                            {
                                input = v,
                                output = new OutputData
                                {
                                    Type = "command",
                                    parameters_keys = new List<string> { entry.key },
                                    parameters_values = new List<string> { entry.value }
                                }
                            });
                        }
                    }
                }
            }
        }

        // ---- 1c. command_char defaults ----
        private void GenerateCharCommandDefaults(List<DataPoint> newPoints)
        {
            if (variationConfig?.@char == null) return;

            foreach (var entry in _commandCharDefaults)
            {
                if (!variationConfig.@char.TryGetValue(entry.key, out var charValues)) continue;
                if (entry.input == null) continue;

                foreach (var inputPhrase in entry.input)
                {
                    var phraseVariants = GetVariants(inputPhrase, maxRandomVariantsSingle);

                    foreach (var charVal in charValues)
                    {
                        foreach (var variant in phraseVariants)
                        {
                            newPoints.Add(new DataPoint
                            {
                                input = $"{variant} {charVal}",
                                output = new OutputData
                                {
                                    Type = "command",
                                    parameters_keys = new List<string> { entry.key },
                                    parameters_values = new List<string> { charVal }
                                }
                            });
                        }
                    }
                }
            }
        }

        // ---- 1d. command_float defaults ----
        private void GenerateFloatCommandDefaults(List<DataPoint> newPoints)
        {
            if (variationConfig?.@float == null) return;

            foreach (var entry in _commandFloatDefaults)
            {
                if (!variationConfig.@float.TryGetValue(entry.key, out var range) || range.Count < 2) continue;
                if (entry.input == null) continue;

                double min = range[0];
                double max = range[1];

                foreach (var inputPhrase in entry.input)
                {
                    var phraseVariants = GetVariants(inputPhrase, maxRandomVariantsSingle);

                    var guaranteedValues = new List<string>
                    {
                        ((int)Math.Floor(min)).ToString(),
                        ((int)Math.Ceiling((min + max) / 2.0)).ToString(),
                        ((int)Math.Floor(max)).ToString()
                    };

                    foreach (var intVal in guaranteedValues)
                    {
                        string variant = phraseVariants[_random.Next(phraseVariants.Count)];
                        newPoints.Add(new DataPoint
                        {
                            input = $"{variant} {intVal}",
                            output = new OutputData
                            {
                                Type = "command",
                                parameters_keys = new List<string> { entry.key },
                                parameters_values = new List<string> { intVal }
                            }
                        });
                    }

                    for (int n = 0; n < maxFloatDoubleLines; n++)
                    {
                        float value = (float)(min + _random.NextDouble() * (max - min));
                        string valueStr = value.ToString("0.##");
                        string variant = phraseVariants[_random.Next(phraseVariants.Count)];

                        newPoints.Add(new DataPoint
                        {
                            input = $"{variant} {valueStr}",
                            output = new OutputData
                            {
                                Type = "command",
                                parameters_keys = new List<string> { entry.key },
                                parameters_values = new List<string> { valueStr }
                            }
                        });
                    }
                }
            }
        }

        // ---- 1e. command_double defaults ----
        private void GenerateDoubleCommandDefaults(List<DataPoint> newPoints)
        {
            if (variationConfig?.@double == null) return;

            foreach (var entry in _commandDoubleDefaults)
            {
                if (!variationConfig.@double.TryGetValue(entry.key, out var range) || range.Count < 2) continue;
                if (entry.input == null) continue;

                double min = range[0];
                double max = range[1];

                foreach (var inputPhrase in entry.input)
                {
                    var phraseVariants = GetVariants(inputPhrase, maxRandomVariantsSingle);

                    var guaranteedValues = new List<string>
                    {
                        ((int)Math.Floor(min)).ToString(),
                        ((int)Math.Ceiling((min + max) / 2.0)).ToString(),
                        ((int)Math.Floor(max)).ToString()
                    };

                    foreach (var intVal in guaranteedValues)
                    {
                        string variant = phraseVariants[_random.Next(phraseVariants.Count)];
                        newPoints.Add(new DataPoint
                        {
                            input = $"{variant} {intVal}",
                            output = new OutputData
                            {
                                Type = "command",
                                parameters_keys = new List<string> { entry.key },
                                parameters_values = new List<string> { intVal }
                            }
                        });
                    }

                    for (int n = 0; n < maxFloatDoubleLines; n++)
                    {
                        double value = min + _random.NextDouble() * (max - min);
                        string valueStr = value.ToString("0.##");
                        string variant = phraseVariants[_random.Next(phraseVariants.Count)];

                        newPoints.Add(new DataPoint
                        {
                            input = $"{variant} {valueStr}",
                            output = new OutputData
                            {
                                Type = "command",
                                parameters_keys = new List<string> { entry.key },
                                parameters_values = new List<string> { valueStr }
                            }
                        });
                    }
                }
            }
        }

        // ---- 2. Clarification defaults ----
        private void GenerateClarificationDefaults(List<DataPoint> newPoints)
        {
            foreach (var entry in _clarificationDefaults)
            {
                if (entry.input == null) continue;

                foreach (var inputPhrase in entry.input)
                {
                    var variants = GetVariants(inputPhrase, maxRandomVariantsMulti);

                    foreach (var v in variants)
                    {
                        newPoints.Add(new DataPoint
                        {
                            input = v,
                            output = new OutputData
                            {
                                Type = "clarification",
                                message = entry.message
                            }
                        });
                    }
                }
            }
        }

        // ---- 3. Extra types (error, exit, mode_lenient, mode_strict) ----
        private void GenerateExtraTypeDefaults(List<DataPoint> newPoints)
        {
            var errorPhrases = GetModeFilteredInputs(_errorDefaultPhrases, _errorStrictPhrases, null);
            foreach (var inputPhrase in errorPhrases)
            {
                var variants = GetVariants(inputPhrase, maxRandomVariantsMulti);
                foreach (var v in variants)
                {
                    newPoints.Add(new DataPoint
                    {
                        input = v,
                        output = new OutputData { Type = "error", message = _errorMessage }
                    });
                }
            }

            var exitPhrases = GetModeFilteredInputs(
                _exitDefaults.SelectMany(e => e.input ?? new List<string>()).ToList(),
                null,
                _exitLenient.SelectMany(e => e.input ?? new List<string>()).ToList());

            foreach (var inputPhrase in exitPhrases)
            {
                var variants = GetVariants(inputPhrase, maxRandomVariantsMulti);
                foreach (var v in variants)
                    newPoints.Add(new DataPoint { input = v, output = new OutputData { Type = "exit" } });
            }

            foreach (var entry in _modeDefaults)
            {
                if (entry.input == null || entry.type == null) continue;

                foreach (var inputPhrase in entry.input)
                {
                    var variants = GetVariants(inputPhrase, maxRandomVariantsMulti);
                    foreach (var v in variants)
                        newPoints.Add(new DataPoint { input = v, output = new OutputData { Type = entry.type } });
                }
            }
        }

        // ---- 4. Multi-command combinations ----
        private void GenerateMultiCommandCombinations(List<DataPoint> newPoints)
        {
            var singleEntries = GetCurrentBoolCommandEntries();
            if (singleEntries.Count == 0) return;

            var allKeys = singleEntries.Select(e => e.key).Distinct().ToList();
            var boolValues = new[] { "true", "false" };
            var random = new Random();

            for (int size = 2; size <= allKeys.Count; size++)
            {
                foreach (var keySubset in GetCombinations(allKeys, size))
                {
                    for (int variantIndex = 0; variantIndex < maxRandomVariantsMulti; variantIndex++)
                    {
                        var keyValuePairs = keySubset.ToDictionary(
                            k => k,
                            k => boolValues[random.Next(boolValues.Length)]
                        );

                        var groups = new List<(string phrase, List<string> keys)>();
                        bool skip = false;

                        foreach (var group in keyValuePairs.GroupBy(kv => kv.Value))
                        {
                            var groupPhrases = new List<string>();
                            var groupKeys = new List<string>();
                            foreach (var key in group.Select(g => g.Key))
                            {
                                var entry = singleEntries.FirstOrDefault(d => d.key == key && d.value == group.Key);
                                if (entry == null || entry.input == null) { skip = true; break; }
                                groupPhrases.Add(entry.input[random.Next(entry.input.Count)]);
                                groupKeys.Add(key);
                            }
                            if (skip) break;

                            var paired = groupPhrases
                                .Zip(groupKeys, (p, k) => (phrase: p, key: k))
                                .OrderBy(x =>
                                {
                                    var m = Regex.Match(x.phrase, @"\d+");
                                    return m.Success ? int.Parse(m.Value) : int.MaxValue;
                                })
                                .ToList();

                            groups.Add((
                                CombineCommandPhrases(paired.Select(x => x.phrase).ToList()),
                                paired.Select(x => x.key).ToList()
                            ));
                        }
                        if (skip) continue;

                        groups = groups.OrderBy(_ => random.Next()).ToList();

                        string finalInput = string.Join(" and ", groups.Select(g => g.phrase));
                        var orderedKeys = groups.SelectMany(g => g.keys).ToList();

                        newPoints.Add(new DataPoint
                        {
                            input = finalInput,
                            output = new OutputData
                            {
                                Type = "command",
                                parameters_keys = orderedKeys,
                                parameters_values = orderedKeys.Select(k => keyValuePairs[k]).ToList()
                            }
                        });
                    }
                }
            }
        }

        // ---- 5. Multi-defaults + non-covered parameter combinations ----
        private void GenerateMultiDefaultsCombinations(List<DataPoint> newPoints)
        {
            var allEngineEntries = GetCurrentAllEngineEntries();
            if (allEngineEntries.Count == 0) return;

            var singleEntries = GetCurrentBoolCommandEntries();
            if (singleEntries.Count == 0) return;

            var random = new Random();

            var multiDefaultCoveredKeys = new HashSet<string>(
                allEngineEntries.SelectMany(e => e.keys)
            );

            var extraParams = config.parameters
                .Select(p => p.key)
                .Where(k => !multiDefaultCoveredKeys.Contains(k))
                .Where(k => singleEntries.Any(e => e.key == k))
                .ToList();

            IEnumerable<Dictionary<string, string>> CartesianExtraParams(List<string> keys)
            {
                IEnumerable<Dictionary<string, string>> acc =
                    new List<Dictionary<string, string>> { new Dictionary<string, string>() };

                foreach (var key in keys)
                {
                    acc = acc.SelectMany(existing =>
                        new[] { "true", "false" }.Select(val =>
                        {
                            var next = new Dictionary<string, string>(existing) { [key] = val };
                            return next;
                        })
                    );
                }
                return acc;
            }

            foreach (var multiDef in allEngineEntries)
            {
                if (multiDef.input == null) continue;

                var multiPhraseVariants = multiDef.input
                    .SelectMany(phrase => GetVariants(phrase, maxRandomVariantsMulti))
                    .Distinct()
                    .Take(maxRandomVariantsMulti)
                    .ToList();

                if (extraParams.Count == 0)
                {
                    foreach (var phrase in multiPhraseVariants)
                    {
                        newPoints.Add(new DataPoint
                        {
                            input = phrase,
                            output = new OutputData
                            {
                                Type = "command",
                                parameters_keys = new List<string>(multiDef.keys),
                                parameters_values = new List<string>(multiDef.values)
                            }
                        });
                    }
                    continue;
                }

                foreach (var extraAssignment in CartesianExtraParams(extraParams))
                {
                    var extraPhrases = new List<(string phrase, string key, string value)>();
                    bool skip = false;

                    foreach (var kvp in extraAssignment)
                    {
                        var entry = singleEntries.FirstOrDefault(d => d.key == kvp.Key && d.value == kvp.Value);
                        if (entry == null || entry.input == null) { skip = true; break; }

                        var basePhrase = entry.input[random.Next(entry.input.Count)];
                        var variantPhrases = GetVariants(basePhrase, maxRandomVariantsMulti);
                        extraPhrases.Add((variantPhrases[random.Next(variantPhrases.Count)], kvp.Key, kvp.Value));
                    }
                    if (skip) continue;

                    foreach (var multiPhrase in multiPhraseVariants)
                    {
                        var groups = new List<(string phrase, List<string> keys, List<string> values)>
                        {
                            (multiPhrase, new List<string>(multiDef.keys), new List<string>(multiDef.values)),
                            (
                                string.Join(" and ", extraPhrases.Select(ep => ep.phrase)),
                                extraPhrases.Select(ep => ep.key).ToList(),
                                extraPhrases.Select(ep => ep.value).ToList()
                            )
                        };

                        groups = groups.OrderBy(_ => random.Next()).ToList();

                        string finalInput = string.Join(" and ", groups.Select(g => g.phrase));
                        var orderedKeys = groups.SelectMany(g => g.keys).ToList();
                        var orderedValues = groups.SelectMany(g => g.values).ToList();

                        newPoints.Add(new DataPoint
                        {
                            input = finalInput,
                            output = new OutputData
                            {
                                Type = "command",
                                parameters_keys = orderedKeys,
                                parameters_values = orderedValues
                            }
                        });
                    }
                }
            }
        }

        // ---- 6. Multi-level clarification ----
        private void GenerateMultiLevelClarification(List<DataPoint> newPoints)
        {
            var singleEntries = GetCurrentBoolCommandEntries();
            if (singleEntries.Count == 0 || _clarificationDefaults.Count == 0) return;

            var random = new Random();

            foreach (var clarEntry in _clarificationDefaults)
            {
                if (clarEntry.excluded_keys == null || clarEntry.excluded_keys.Count == 0)
                    continue;
                if (clarEntry.input == null) continue;

                var excludedKeys = new HashSet<string>(clarEntry.excluded_keys);

                var eligibleKeys = config.parameters
                    .Select(p => p.key)
                    .Where(k => !excludedKeys.Contains(k))
                    .Where(k => singleEntries.Any(e => e.key == k))
                    .ToList();

                if (eligibleKeys.Count == 0) continue;

                var eligibleSubsets = new List<List<string>>();
                for (int size = 1; size <= eligibleKeys.Count; size++)
                    eligibleSubsets.AddRange(GetCombinations(eligibleKeys, size));

                var boolValues = new[] { "true", "false" };

                foreach (var clarInputPhrase in clarEntry.input)
                {
                    var clarVariants = GetVariants(clarInputPhrase, maxRandomVariantsSingle);

                    foreach (var keySubset in eligibleSubsets)
                    {
                        var keyValuePairs = keySubset.ToDictionary(
                            k => k,
                            k => boolValues[random.Next(boolValues.Length)]
                        );

                        var commandParts = new List<string>();
                        bool skip = false;

                        foreach (var group in keyValuePairs.GroupBy(kv => kv.Value))
                        {
                            var groupPhrases = new List<string>();
                            foreach (var key in group.Select(g => g.Key))
                            {
                                var cmdEntry = singleEntries.FirstOrDefault(d => d.key == key && d.value == group.Key);
                                if (cmdEntry == null || cmdEntry.input == null) { skip = true; break; }
                                groupPhrases.Add(cmdEntry.input[random.Next(cmdEntry.input.Count)]);
                            }
                            if (skip) break;
                            commandParts.Add(CombineCommandPhrases(groupPhrases));
                        }
                        if (skip) continue;

                        string clarPhrase = clarVariants[random.Next(clarVariants.Count)];

                        var allParts = new List<string> { clarPhrase };
                        allParts.AddRange(commandParts);
                        allParts = allParts.OrderBy(_ => random.Next()).ToList();

                        newPoints.Add(new DataPoint
                        {
                            input = string.Join(" and ", allParts),
                            output = new OutputData
                            {
                                Type = "clarification",
                                parameters_keys = keySubset.ToList(),
                                parameters_values = keySubset.Select(k => keyValuePairs[k]).ToList(),
                                message = clarEntry.message
                            }
                        });
                    }
                }
            }
        }

        // ---- 7. Multi-level value errors ----
        private void GenerateMultiLevelValueErrors(List<DataPoint> newPoints)
        {
            if (_clarificationDefaults.Count == 0) return;

            var random = new Random();

            var clarEntries = _clarificationDefaults
                .Where(c => c.excluded_keys != null && c.excluded_keys.Count > 0 && c.input != null)
                .ToList();

            for (int size = 2; size <= clarEntries.Count; size++)
            {
                foreach (var clarSubset in GetCombinations(clarEntries, size))
                {
                    var parts = new List<string>();

                    foreach (var clarEntry in clarSubset)
                    {
                        string basePhrase = clarEntry.input[random.Next(clarEntry.input.Count)];
                        var variants = GetVariants(basePhrase, maxRandomVariantsSingle);
                        parts.Add(variants[random.Next(variants.Count)]);
                    }

                    parts = parts.OrderBy(_ => random.Next()).ToList();

                    newPoints.Add(new DataPoint
                    {
                        input = string.Join(" and ", parts),
                        output = new OutputData
                        {
                            Type = "error",
                            message = _multiLevelErrorMessage
                        }
                    });
                }
            }
        }

        // ---- 8. Multi-level errors ----
        private void GenerateMultiLevelErrors(List<DataPoint> newPoints)
        {
            var allErrorPhrases = GetModeFilteredInputs(_errorDefaultPhrases, _errorStrictPhrases, null)
                .Distinct()
                .ToList();

            if (allErrorPhrases.Count == 0) return;

            var random = new Random();
            int maxErrorComboSize = Math.Min(3, allErrorPhrases.Count);

            for (int size = 2; size <= maxErrorComboSize; size++)
            {
                for (int i = 0; i < maxRandomVariantsSingle; i++)
                {
                    var shuffled = allErrorPhrases.OrderBy(_ => random.Next()).Take(size).ToList();

                    var parts = new List<string>();
                    foreach (var phrase in shuffled)
                    {
                        var variants = GetVariants(phrase, maxRandomVariantsSingle);
                        parts.Add(variants[random.Next(variants.Count)]);
                    }

                    newPoints.Add(new DataPoint
                    {
                        input = string.Join(" and ", parts),
                        output = new OutputData
                        {
                            Type = "error",
                            message = "command not recognized"
                        }
                    });
                }
            }
        }

        // ---- 9. Approach defaults ----
        private void GenerateApproachDefaults(List<DataPoint> newPoints)
        {
            if (_approachEntries == null || _approachEntries.Count == 0) return;
            if (variationConfig?.@char == null) return;
            if (!variationConfig.@char.TryGetValue("ICAO", out var ICAOs) || ICAOs.Count == 0) return;

            foreach (var entry in _approachEntries)
            {
                if (entry.input == null) continue;

                foreach (var ICAO in ICAOs)
                {
                    var substitution = BuildApproachSubstitution(entry, ICAO);
                    if (substitution == null) continue;

                    foreach (var inputTemplate in entry.input)
                    {
                        string resolvedInput = ResolveApproachPlaceholders(inputTemplate, substitution);

                        var resolvedValues = entry.values
                            .Select(v => ResolveApproachPlaceholders(v, substitution))
                            .ToList();

                        newPoints.Add(new DataPoint
                        {
                            input = resolvedInput,
                            output = new OutputData
                            {
                                Type = "command",
                                parameters_keys = new List<string>(entry.keys),
                                parameters_values = resolvedValues
                            }
                        });
                    }
                }

                for (int n = 0; n < maxFloatDoubleLines; n++)
                {
                    string ICAO = ICAOs[_random.Next(ICAOs.Count)];
                    var substitution = BuildApproachSubstitution(entry, ICAO);
                    if (substitution == null) continue;

                    foreach (var inputTemplate in entry.input)
                    {
                        string resolvedInput = ResolveApproachPlaceholders(inputTemplate, substitution);

                        var resolvedValues = entry.values
                            .Select(v => ResolveApproachPlaceholders(v, substitution))
                            .ToList();

                        newPoints.Add(new DataPoint
                        {
                            input = resolvedInput,
                            output = new OutputData
                            {
                                Type = "command",
                                parameters_keys = new List<string>(entry.keys),
                                parameters_values = resolvedValues
                            }
                        });
                    }
                }
            }
        }

        // ---- 10. Multi-default clarifications with allowed combinations ----
        private void GenerateMultiDefaultAllowedClarifications(List<DataPoint> newPoints)
        {
            if (_multiClarificationAllowed == null || _multiClarificationAllowed.Count == 0) return;

            var engineTrueKeys = new HashSet<string> { "ENGINE_1_MALF", "ENGINE_2_MALF", "ENGINE_3_MALF", "ENGINE_4_MALF" };

            foreach (var clarEntry in _multiClarificationAllowed)
            {
                if (clarEntry.input == null || clarEntry.allowed == null) continue;

                var allowed = clarEntry.allowed;

                var validSubsets = new List<List<AllowedEntry>>();
                for (int size = 1; size <= allowed.Count; size++)
                {
                    foreach (var subset in GetCombinations(allowed, size))
                    {
                        var keys = subset.Select(e => e.key).ToList();
                        if (keys.Count != keys.Distinct().Count()) continue;

                        int engineTrueCount = subset.Count(e => engineTrueKeys.Contains(e.key) && e.value == "true");
                        int engineFalseCount = subset.Count(e => engineTrueKeys.Contains(e.key) && e.value == "false");
                        if (engineTrueCount > 1 || engineFalseCount > 1) continue;

                        validSubsets.Add(subset);
                    }
                }

                if (validSubsets.Count == 0) continue;

                if (validSubsets.Count > maxRandomVariantsMulti * 5)
                {
                    validSubsets = validSubsets
                        .OrderBy(_ => _random.Next())
                        .Take(maxRandomVariantsMulti * 5)
                        .ToList();
                }

                foreach (var subset in validSubsets)
                {
                    var allowedPhrases = subset
                        .Select(e => e.input[_random.Next(e.input.Count)])
                        .ToList();

                    foreach (var clarInputPhrase in clarEntry.input)
                    {
                        var clarVariants = GetVariants(clarInputPhrase, maxRandomVariantsSingle);
                        string clarPhrase = clarVariants[_random.Next(clarVariants.Count)];

                        var parts = new List<string> { clarPhrase };
                        parts.AddRange(allowedPhrases);
                        parts = parts.OrderBy(_ => _random.Next()).ToList();

                        string finalInput = string.Join(" and ", parts);

                        var outKeys = new List<string>();
                        var outValues = new List<string>();

                        if (clarEntry.keys != null && clarEntry.keys.Count > 0)
                        {
                            outKeys.AddRange(clarEntry.keys);
                            outValues.AddRange(clarEntry.values ?? Enumerable.Repeat("", clarEntry.keys.Count).ToList());
                        }

                        foreach (var ae in subset)
                        {
                            outKeys.Add(ae.key);
                            outValues.Add(ae.value);
                        }

                        newPoints.Add(new DataPoint
                        {
                            input = finalInput,
                            output = new OutputData
                            {
                                Type = "clarification",
                                parameters_keys = outKeys,
                                parameters_values = outValues,
                                message = clarEntry.message
                            }
                        });
                    }
                }
            }
        }

        private Dictionary<string, string> BuildApproachSubstitution(ApproachEntry entry, string ICAO)
        {
            var sub = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
            {
                ["ICAO_VAL"] = ICAO
            };

            foreach (var key in entry.keys)
            {
                string placeholder = key + "_VAL";
                if (sub.ContainsKey(placeholder)) continue;
                if (!entry.values.Any(v => v.Contains(placeholder))) continue;

                if (variationConfig.@float != null &&
                    variationConfig.@float.TryGetValue(key, out var floatRange) &&
                    floatRange.Count >= 2)
                {
                    float val = (float)(floatRange[0] + _random.NextDouble() * (floatRange[1] - floatRange[0]));
                    sub[placeholder] = val.ToString("0.##");
                    continue;
                }

                if (variationConfig.@double != null &&
                    variationConfig.@double.TryGetValue(key, out var doubleRange) &&
                    doubleRange.Count >= 2)
                {
                    double val = doubleRange[0] + _random.NextDouble() * (doubleRange[1] - doubleRange[0]);
                    sub[placeholder] = val.ToString("0.##");
                    continue;
                }

                if (variationConfig.@char != null &&
                    variationConfig.@char.TryGetValue(key, out var charVals) &&
                    charVals.Count > 0)
                {
                    sub[placeholder] = charVals[_random.Next(charVals.Count)];
                    continue;
                }

                return null;
            }

            return sub;
        }

        private string ResolveApproachPlaceholders(string template, Dictionary<string, string> substitution)
        {
            string result = template;
            foreach (var kvp in substitution)
                result = Regex.Replace(result, Regex.Escape(kvp.Key), kvp.Value, RegexOptions.IgnoreCase);
            return result;
        }

        // =========================
        // Phrase combination helpers
        // =========================
        private string CombineCommandPhrases(List<string> phrases)
        {
            if (phrases.Count == 1) return phrases[0];

            var enginePhrases = phrases
                .Where(p => Regex.IsMatch(p, @"engine \d+", RegexOptions.IgnoreCase))
                .ToList();

            var otherPhrases = phrases
                .Where(p => !Regex.IsMatch(p, @"engine \d+", RegexOptions.IgnoreCase))
                .ToList();

            var parts = new List<string>();
            if (enginePhrases.Count > 0)
                parts.Add(CompactEnginePhrases(enginePhrases));
            parts.AddRange(otherPhrases);

            return string.Join(" and ", parts);
        }

        private string CompactEnginePhrases(List<string> phrases)
        {
            if (phrases.Count == 1) return phrases[0];

            var numberGroups = new List<string>();
            string prefix = null;
            string suffix = null;

            phrases = phrases
                .OrderBy(ph => {
                    var m = Regex.Match(ph, @"\d+");
                    return m.Success ? int.Parse(m.Value) : int.MaxValue;
                })
                .ToList();

            foreach (var ph in phrases)
            {
                var match = Regex.Match(ph, @"\d+");
                if (!match.Success) continue;

                numberGroups.Add(match.Value);

                if (prefix == null)
                    prefix = ph.Substring(0, match.Index).Trim();

                if (suffix == null)
                    suffix = ph.Substring(match.Index + match.Length).Trim();
            }

            if (numberGroups.Count == 0) return string.Join(" and ", phrases);

            string numbersCombined = numberGroups.Count == 1
                ? numberGroups[0]
                : string.Join(", ", numberGroups.Take(numberGroups.Count - 1)) + " and " + numberGroups.Last();

            return $"{prefix} engine {numbersCombined} {suffix}".Trim();
        }

        // =========================
        // Manual line generation
        // =========================
        private void button_GenerateLines_Click(object sender, EventArgs e)
        {
            string baseInput = textBox_Input.Text.Trim();
            if (string.IsNullOrEmpty(baseInput)) return;

            var newPoints = new List<DataPoint>();
            GenerateSimple(baseInput, new List<string>(), new List<string>(), comboBox_Type.SelectedItem?.ToString(), newPoints);

            newPoints = newPoints
                .Where(dp => !string.IsNullOrWhiteSpace(dp.input))
                .GroupBy(dp => dp.input.ToLower().Trim())
                .Select(g => g.First())
                .ToList();

            SaveToJsonl(newPoints);
        }

        private void GenerateSimple(string baseInput, List<string> keys, List<string> values, string type, List<DataPoint> newPoints)
        {
            var variants = GetVariants(baseInput, maxRandomVariantsSingle);

            foreach (var v in variants)
            {
                newPoints.Add(new DataPoint
                {
                    input = v,
                    output = new OutputData
                    {
                        Type = type,
                        parameters_keys = keys.Count > 0 ? keys : null,
                        parameters_values = values.Count > 0 ? values : null
                    }
                });
            }
        }

        private void button_Restart_Click(object sender, EventArgs e)
        {
            textBox_Input.Clear();
            PopulateMultiGrid();
        }

        // =========================
        // Save
        // =========================
        private void SaveToJsonl(List<DataPoint> points)
        {
            try
            {
                var existingInputs = new HashSet<string>();

                if (File.Exists(filePath))
                {
                    foreach (var line in File.ReadAllLines(filePath))
                    {
                        if (string.IsNullOrWhiteSpace(line)) continue;
                        try
                        {
                            var existing = JsonSerializer.Deserialize<DataPoint>(line);
                            if (existing?.input != null)
                                existingInputs.Add(existing.input.ToLower().Trim());
                        }
                        catch { }
                    }
                }

                int skipped = 0, added = 0;

                var writer = new StreamWriter(filePath, true);
                foreach (var dp in points)
                {
                    if (string.IsNullOrWhiteSpace(dp.input)) { skipped++; continue; }
                    string key = dp.input.ToLower().Trim();
                    if (existingInputs.Contains(key)) { skipped++; continue; }

                    writer.WriteLine(JsonSerializer.Serialize(dp));
                    existingInputs.Add(key);
                    added++;
                }
                writer.Close();

                MessageBox.Show($"Saved {added} new line(s). Skipped {skipped} duplicate(s).");
            }
            catch (Exception ex)
            {
                MessageBox.Show("Error saving to dataset.jsonl:\n" + ex.Message);
            }
        }
    }
}