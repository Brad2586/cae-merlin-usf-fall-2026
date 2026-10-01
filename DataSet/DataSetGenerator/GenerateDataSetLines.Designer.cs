namespace DataSetGenerator
{
    partial class DataSetGeneration
    {
        /// <summary>
        /// Required designer variable.
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        /// Clean up any resources being used.
        /// </summary>
        /// <param name="disposing">true if managed resources should be disposed; otherwise, false.</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows Form Designer generated code

        /// <summary>
        /// Required method for Designer support - do not modify
        /// the contents of this method with the code editor.
        /// </summary>
        private void InitializeComponent()
        {
            this.textBox_Input = new System.Windows.Forms.TextBox();
            this.comboBox_SingleParameterKey = new System.Windows.Forms.ComboBox();
            this.dataGridView_Multi = new System.Windows.Forms.DataGridView();
            this.ParameterKey = new System.Windows.Forms.DataGridViewCheckBoxColumn();
            this.Value = new System.Windows.Forms.DataGridViewComboBoxColumn();
            this.radioButton_Single = new System.Windows.Forms.RadioButton();
            this.radioButton_Multi = new System.Windows.Forms.RadioButton();
            this.label_Input = new System.Windows.Forms.Label();
            this.groupBox_SingleCommand = new System.Windows.Forms.GroupBox();
            this.comboBox_ParameterValueSingle = new System.Windows.Forms.ComboBox();
            this.label_ParameterValueSingle = new System.Windows.Forms.Label();
            this.label_ParameterKeySingle = new System.Windows.Forms.Label();
            this.label_Type = new System.Windows.Forms.Label();
            this.comboBox_Type = new System.Windows.Forms.ComboBox();
            this.label_Message = new System.Windows.Forms.Label();
            this.groupBox_MultiCommand = new System.Windows.Forms.GroupBox();
            this.button_GenerateLines = new System.Windows.Forms.Button();
            this.button_Restart = new System.Windows.Forms.Button();
            this.checkBox_Variations = new System.Windows.Forms.CheckBox();
            this.comboBox_Message = new System.Windows.Forms.ComboBox();
            this.checkBox_NumberExpansion = new System.Windows.Forms.CheckBox();
            this.button_Defaults = new System.Windows.Forms.Button();
            this.comboBox_VariantCountSingle = new System.Windows.Forms.ComboBox();
            this.comboBox_VariantCountMulti = new System.Windows.Forms.ComboBox();
            this.checkBox_GenSingleCommand = new System.Windows.Forms.CheckBox();
            this.checkBox_GenExtraTypes = new System.Windows.Forms.CheckBox();
            this.checkBox_GenClarification = new System.Windows.Forms.CheckBox();
            this.checkBox_GenMultiCommand = new System.Windows.Forms.CheckBox();
            this.checkBox_GenMultiDefaults = new System.Windows.Forms.CheckBox();
            this.checkBox_GenMultiLevelClarification = new System.Windows.Forms.CheckBox();
            this.checkBox_GenMultiLevelValueErrors = new System.Windows.Forms.CheckBox();
            this.checkBox_GenMultiLevelErrors = new System.Windows.Forms.CheckBox();
            this.comboBox_VariantCountFloatDouble = new System.Windows.Forms.ComboBox();
            this.label_VariantCountFloatDouble = new System.Windows.Forms.Label();
            this.label_VariantCountSingle = new System.Windows.Forms.Label();
            this.label_VariantCountMulti = new System.Windows.Forms.Label();
            this.checkBox_GenApproach = new System.Windows.Forms.CheckBox();
            this.groupBox_GenerationMode = new System.Windows.Forms.GroupBox();
            this.radioButton_ModeStrict = new System.Windows.Forms.RadioButton();
            this.radioButton_ModeLenient = new System.Windows.Forms.RadioButton();
            ((System.ComponentModel.ISupportInitialize)(this.dataGridView_Multi)).BeginInit();
            this.groupBox_SingleCommand.SuspendLayout();
            this.groupBox_MultiCommand.SuspendLayout();
            this.groupBox_GenerationMode.SuspendLayout();
            this.SuspendLayout();
            // 
            // textBox_Input
            // 
            this.textBox_Input.Location = new System.Drawing.Point(33, 116);
            this.textBox_Input.Name = "textBox_Input";
            this.textBox_Input.Size = new System.Drawing.Size(1091, 20);
            this.textBox_Input.TabIndex = 0;
            // 
            // comboBox_SingleParameterKey
            // 
            this.comboBox_SingleParameterKey.FormattingEnabled = true;
            this.comboBox_SingleParameterKey.Location = new System.Drawing.Point(0, 39);
            this.comboBox_SingleParameterKey.Name = "comboBox_SingleParameterKey";
            this.comboBox_SingleParameterKey.Size = new System.Drawing.Size(121, 21);
            this.comboBox_SingleParameterKey.TabIndex = 1;
            // 
            // dataGridView_Multi
            // 
            this.dataGridView_Multi.ColumnHeadersHeightSizeMode = System.Windows.Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize;
            this.dataGridView_Multi.Columns.AddRange(new System.Windows.Forms.DataGridViewColumn[] {
            this.ParameterKey,
            this.Value});
            this.dataGridView_Multi.Location = new System.Drawing.Point(6, 39);
            this.dataGridView_Multi.Name = "dataGridView_Multi";
            this.dataGridView_Multi.Size = new System.Drawing.Size(254, 155);
            this.dataGridView_Multi.TabIndex = 2;
            // 
            // ParameterKey
            // 
            this.ParameterKey.HeaderText = "Parameter Key";
            this.ParameterKey.Name = "ParameterKey";
            // 
            // Value
            // 
            this.Value.HeaderText = "Value";
            this.Value.Items.AddRange(new object[] {
            "True",
            "False"});
            this.Value.Name = "Value";
            // 
            // radioButton_Single
            // 
            this.radioButton_Single.AutoSize = true;
            this.radioButton_Single.Location = new System.Drawing.Point(33, 32);
            this.radioButton_Single.Name = "radioButton_Single";
            this.radioButton_Single.Size = new System.Drawing.Size(104, 17);
            this.radioButton_Single.TabIndex = 3;
            this.radioButton_Single.TabStop = true;
            this.radioButton_Single.Text = "Single Command";
            this.radioButton_Single.UseVisualStyleBackColor = true;
            // 
            // radioButton_Multi
            // 
            this.radioButton_Multi.AutoSize = true;
            this.radioButton_Multi.Location = new System.Drawing.Point(33, 55);
            this.radioButton_Multi.Name = "radioButton_Multi";
            this.radioButton_Multi.Size = new System.Drawing.Size(126, 17);
            this.radioButton_Multi.TabIndex = 4;
            this.radioButton_Multi.TabStop = true;
            this.radioButton_Multi.Text = "Multi Level Command";
            this.radioButton_Multi.UseVisualStyleBackColor = true;
            // 
            // label_Input
            // 
            this.label_Input.AutoSize = true;
            this.label_Input.Location = new System.Drawing.Point(30, 100);
            this.label_Input.Name = "label_Input";
            this.label_Input.Size = new System.Drawing.Size(59, 13);
            this.label_Input.TabIndex = 5;
            this.label_Input.Text = "User Input:";
            // 
            // groupBox_SingleCommand
            // 
            this.groupBox_SingleCommand.Controls.Add(this.comboBox_ParameterValueSingle);
            this.groupBox_SingleCommand.Controls.Add(this.label_ParameterValueSingle);
            this.groupBox_SingleCommand.Controls.Add(this.label_ParameterKeySingle);
            this.groupBox_SingleCommand.Controls.Add(this.comboBox_SingleParameterKey);
            this.groupBox_SingleCommand.Location = new System.Drawing.Point(33, 227);
            this.groupBox_SingleCommand.Name = "groupBox_SingleCommand";
            this.groupBox_SingleCommand.Size = new System.Drawing.Size(314, 76);
            this.groupBox_SingleCommand.TabIndex = 6;
            this.groupBox_SingleCommand.TabStop = false;
            this.groupBox_SingleCommand.Text = "Single Command Mode";
            // 
            // comboBox_ParameterValueSingle
            // 
            this.comboBox_ParameterValueSingle.FormattingEnabled = true;
            this.comboBox_ParameterValueSingle.Items.AddRange(new object[] {
            "True",
            "False"});
            this.comboBox_ParameterValueSingle.Location = new System.Drawing.Point(175, 38);
            this.comboBox_ParameterValueSingle.Name = "comboBox_ParameterValueSingle";
            this.comboBox_ParameterValueSingle.Size = new System.Drawing.Size(121, 21);
            this.comboBox_ParameterValueSingle.TabIndex = 4;
            // 
            // label_ParameterValueSingle
            // 
            this.label_ParameterValueSingle.AutoSize = true;
            this.label_ParameterValueSingle.Location = new System.Drawing.Point(172, 22);
            this.label_ParameterValueSingle.Name = "label_ParameterValueSingle";
            this.label_ParameterValueSingle.Size = new System.Drawing.Size(34, 13);
            this.label_ParameterValueSingle.TabIndex = 3;
            this.label_ParameterValueSingle.Text = "Value";
            // 
            // label_ParameterKeySingle
            // 
            this.label_ParameterKeySingle.AutoSize = true;
            this.label_ParameterKeySingle.Location = new System.Drawing.Point(-3, 23);
            this.label_ParameterKeySingle.Name = "label_ParameterKeySingle";
            this.label_ParameterKeySingle.Size = new System.Drawing.Size(76, 13);
            this.label_ParameterKeySingle.TabIndex = 2;
            this.label_ParameterKeySingle.Text = "Parameter Key";
            // 
            // label_Type
            // 
            this.label_Type.AutoSize = true;
            this.label_Type.Location = new System.Drawing.Point(30, 137);
            this.label_Type.Name = "label_Type";
            this.label_Type.Size = new System.Drawing.Size(34, 13);
            this.label_Type.TabIndex = 7;
            this.label_Type.Text = "Type:";
            // 
            // comboBox_Type
            // 
            this.comboBox_Type.FormattingEnabled = true;
            this.comboBox_Type.Location = new System.Drawing.Point(33, 153);
            this.comboBox_Type.Name = "comboBox_Type";
            this.comboBox_Type.Size = new System.Drawing.Size(86, 21);
            this.comboBox_Type.TabIndex = 8;
            // 
            // label_Message
            // 
            this.label_Message.AutoSize = true;
            this.label_Message.Location = new System.Drawing.Point(141, 137);
            this.label_Message.Name = "label_Message";
            this.label_Message.Size = new System.Drawing.Size(53, 13);
            this.label_Message.TabIndex = 9;
            this.label_Message.Text = "Message:";
            // 
            // groupBox_MultiCommand
            // 
            this.groupBox_MultiCommand.Controls.Add(this.dataGridView_Multi);
            this.groupBox_MultiCommand.Location = new System.Drawing.Point(372, 180);
            this.groupBox_MultiCommand.Name = "groupBox_MultiCommand";
            this.groupBox_MultiCommand.Size = new System.Drawing.Size(357, 324);
            this.groupBox_MultiCommand.TabIndex = 10;
            this.groupBox_MultiCommand.TabStop = false;
            this.groupBox_MultiCommand.Text = "Multi Command Mode";
            // 
            // button_GenerateLines
            // 
            this.button_GenerateLines.Location = new System.Drawing.Point(33, 490);
            this.button_GenerateLines.Name = "button_GenerateLines";
            this.button_GenerateLines.Size = new System.Drawing.Size(216, 82);
            this.button_GenerateLines.TabIndex = 11;
            this.button_GenerateLines.Text = "Confirm and Generate";
            this.button_GenerateLines.UseVisualStyleBackColor = true;
            // 
            // button_Restart
            // 
            this.button_Restart.Location = new System.Drawing.Point(499, 31);
            this.button_Restart.Name = "button_Restart";
            this.button_Restart.Size = new System.Drawing.Size(129, 40);
            this.button_Restart.TabIndex = 13;
            this.button_Restart.Text = "Restart";
            this.button_Restart.UseVisualStyleBackColor = true;
            // 
            // checkBox_Variations
            // 
            this.checkBox_Variations.AutoSize = true;
            this.checkBox_Variations.Location = new System.Drawing.Point(229, 44);
            this.checkBox_Variations.Name = "checkBox_Variations";
            this.checkBox_Variations.Size = new System.Drawing.Size(143, 17);
            this.checkBox_Variations.TabIndex = 14;
            this.checkBox_Variations.Text = "Generate STT Variations";
            this.checkBox_Variations.UseVisualStyleBackColor = true;
            // 
            // comboBox_Message
            // 
            this.comboBox_Message.FormattingEnabled = true;
            this.comboBox_Message.Location = new System.Drawing.Point(144, 153);
            this.comboBox_Message.Name = "comboBox_Message";
            this.comboBox_Message.Size = new System.Drawing.Size(228, 21);
            this.comboBox_Message.TabIndex = 15;
            // 
            // checkBox_NumberExpansion
            // 
            this.checkBox_NumberExpansion.AutoSize = true;
            this.checkBox_NumberExpansion.Location = new System.Drawing.Point(229, 67);
            this.checkBox_NumberExpansion.Name = "checkBox_NumberExpansion";
            this.checkBox_NumberExpansion.Size = new System.Drawing.Size(140, 17);
            this.checkBox_NumberExpansion.TabIndex = 16;
            this.checkBox_NumberExpansion.Text = "Expand Numbered Keys";
            this.checkBox_NumberExpansion.UseVisualStyleBackColor = true;
            // 
            // button_Defaults
            // 
            this.button_Defaults.Location = new System.Drawing.Point(946, 475);
            this.button_Defaults.Name = "button_Defaults";
            this.button_Defaults.Size = new System.Drawing.Size(166, 97);
            this.button_Defaults.TabIndex = 17;
            this.button_Defaults.Text = "Generate All Defaults";
            this.button_Defaults.UseVisualStyleBackColor = true;
            this.button_Defaults.Click += new System.EventHandler(this.button_Defaults_Click);
            // 
            // comboBox_VariantCountSingle
            // 
            this.comboBox_VariantCountSingle.FormattingEnabled = true;
            this.comboBox_VariantCountSingle.Location = new System.Drawing.Point(883, 427);
            this.comboBox_VariantCountSingle.Name = "comboBox_VariantCountSingle";
            this.comboBox_VariantCountSingle.Size = new System.Drawing.Size(115, 21);
            this.comboBox_VariantCountSingle.TabIndex = 18;
            // 
            // comboBox_VariantCountMulti
            // 
            this.comboBox_VariantCountMulti.FormattingEnabled = true;
            this.comboBox_VariantCountMulti.Location = new System.Drawing.Point(1019, 428);
            this.comboBox_VariantCountMulti.Name = "comboBox_VariantCountMulti";
            this.comboBox_VariantCountMulti.Size = new System.Drawing.Size(119, 21);
            this.comboBox_VariantCountMulti.TabIndex = 19;
            // 
            // checkBox_GenSingleCommand
            // 
            this.checkBox_GenSingleCommand.AutoSize = true;
            this.checkBox_GenSingleCommand.Location = new System.Drawing.Point(883, 192);
            this.checkBox_GenSingleCommand.Name = "checkBox_GenSingleCommand";
            this.checkBox_GenSingleCommand.Size = new System.Drawing.Size(144, 17);
            this.checkBox_GenSingleCommand.TabIndex = 20;
            this.checkBox_GenSingleCommand.Text = "Single command defaults";
            this.checkBox_GenSingleCommand.UseVisualStyleBackColor = true;
            // 
            // checkBox_GenExtraTypes
            // 
            this.checkBox_GenExtraTypes.AutoSize = true;
            this.checkBox_GenExtraTypes.Location = new System.Drawing.Point(883, 238);
            this.checkBox_GenExtraTypes.Name = "checkBox_GenExtraTypes";
            this.checkBox_GenExtraTypes.Size = new System.Drawing.Size(172, 17);
            this.checkBox_GenExtraTypes.TabIndex = 21;
            this.checkBox_GenExtraTypes.Text = "Extra types (error / exit / mode)";
            this.checkBox_GenExtraTypes.UseVisualStyleBackColor = true;
            // 
            // checkBox_GenClarification
            // 
            this.checkBox_GenClarification.AutoSize = true;
            this.checkBox_GenClarification.Location = new System.Drawing.Point(883, 215);
            this.checkBox_GenClarification.Name = "checkBox_GenClarification";
            this.checkBox_GenClarification.Size = new System.Drawing.Size(120, 17);
            this.checkBox_GenClarification.TabIndex = 22;
            this.checkBox_GenClarification.Text = "Clarification defaults";
            this.checkBox_GenClarification.UseVisualStyleBackColor = true;
            // 
            // checkBox_GenMultiCommand
            // 
            this.checkBox_GenMultiCommand.AutoSize = true;
            this.checkBox_GenMultiCommand.Location = new System.Drawing.Point(883, 261);
            this.checkBox_GenMultiCommand.Name = "checkBox_GenMultiCommand";
            this.checkBox_GenMultiCommand.Size = new System.Drawing.Size(162, 17);
            this.checkBox_GenMultiCommand.TabIndex = 23;
            this.checkBox_GenMultiCommand.Text = "Multi-command combinations";
            this.checkBox_GenMultiCommand.UseVisualStyleBackColor = true;
            // 
            // checkBox_GenMultiDefaults
            // 
            this.checkBox_GenMultiDefaults.AutoSize = true;
            this.checkBox_GenMultiDefaults.Location = new System.Drawing.Point(883, 284);
            this.checkBox_GenMultiDefaults.Name = "checkBox_GenMultiDefaults";
            this.checkBox_GenMultiDefaults.Size = new System.Drawing.Size(160, 17);
            this.checkBox_GenMultiDefaults.TabIndex = 24;
            this.checkBox_GenMultiDefaults.Text = "Multi-defaults + extra params";
            this.checkBox_GenMultiDefaults.UseVisualStyleBackColor = true;
            // 
            // checkBox_GenMultiLevelClarification
            // 
            this.checkBox_GenMultiLevelClarification.AutoSize = true;
            this.checkBox_GenMultiLevelClarification.Location = new System.Drawing.Point(883, 307);
            this.checkBox_GenMultiLevelClarification.Name = "checkBox_GenMultiLevelClarification";
            this.checkBox_GenMultiLevelClarification.Size = new System.Drawing.Size(129, 17);
            this.checkBox_GenMultiLevelClarification.TabIndex = 25;
            this.checkBox_GenMultiLevelClarification.Text = "Multi-level clarification";
            this.checkBox_GenMultiLevelClarification.UseVisualStyleBackColor = true;
            // 
            // checkBox_GenMultiLevelValueErrors
            // 
            this.checkBox_GenMultiLevelValueErrors.AutoSize = true;
            this.checkBox_GenMultiLevelValueErrors.Location = new System.Drawing.Point(883, 330);
            this.checkBox_GenMultiLevelValueErrors.Name = "checkBox_GenMultiLevelValueErrors";
            this.checkBox_GenMultiLevelValueErrors.Size = new System.Drawing.Size(131, 17);
            this.checkBox_GenMultiLevelValueErrors.TabIndex = 26;
            this.checkBox_GenMultiLevelValueErrors.Text = "Multi-level value errors";
            this.checkBox_GenMultiLevelValueErrors.UseVisualStyleBackColor = true;
            // 
            // checkBox_GenMultiLevelErrors
            // 
            this.checkBox_GenMultiLevelErrors.AutoSize = true;
            this.checkBox_GenMultiLevelErrors.Location = new System.Drawing.Point(883, 353);
            this.checkBox_GenMultiLevelErrors.Name = "checkBox_GenMultiLevelErrors";
            this.checkBox_GenMultiLevelErrors.Size = new System.Drawing.Size(102, 17);
            this.checkBox_GenMultiLevelErrors.TabIndex = 27;
            this.checkBox_GenMultiLevelErrors.Text = "Multi-level errors";
            this.checkBox_GenMultiLevelErrors.UseVisualStyleBackColor = true;
            // 
            // comboBox_VariantCountFloatDouble
            // 
            this.comboBox_VariantCountFloatDouble.FormattingEnabled = true;
            this.comboBox_VariantCountFloatDouble.Location = new System.Drawing.Point(736, 427);
            this.comboBox_VariantCountFloatDouble.Name = "comboBox_VariantCountFloatDouble";
            this.comboBox_VariantCountFloatDouble.Size = new System.Drawing.Size(121, 21);
            this.comboBox_VariantCountFloatDouble.TabIndex = 28;
            // 
            // label_VariantCountFloatDouble
            // 
            this.label_VariantCountFloatDouble.AutoSize = true;
            this.label_VariantCountFloatDouble.Location = new System.Drawing.Point(733, 411);
            this.label_VariantCountFloatDouble.Name = "label_VariantCountFloatDouble";
            this.label_VariantCountFloatDouble.Size = new System.Drawing.Size(134, 13);
            this.label_VariantCountFloatDouble.TabIndex = 29;
            this.label_VariantCountFloatDouble.Text = "Variant Count Float Double";
            // 
            // label_VariantCountSingle
            // 
            this.label_VariantCountSingle.AutoSize = true;
            this.label_VariantCountSingle.Location = new System.Drawing.Point(880, 411);
            this.label_VariantCountSingle.Name = "label_VariantCountSingle";
            this.label_VariantCountSingle.Size = new System.Drawing.Size(103, 13);
            this.label_VariantCountSingle.TabIndex = 30;
            this.label_VariantCountSingle.Text = "Variant Count Single";
            // 
            // label_VariantCountMulti
            // 
            this.label_VariantCountMulti.AutoSize = true;
            this.label_VariantCountMulti.Location = new System.Drawing.Point(1016, 412);
            this.label_VariantCountMulti.Name = "label_VariantCountMulti";
            this.label_VariantCountMulti.Size = new System.Drawing.Size(96, 13);
            this.label_VariantCountMulti.TabIndex = 31;
            this.label_VariantCountMulti.Text = "Variant Count Multi";
            // 
            // checkBox_GenApproach
            // 
            this.checkBox_GenApproach.AutoSize = true;
            this.checkBox_GenApproach.Location = new System.Drawing.Point(883, 376);
            this.checkBox_GenApproach.Name = "checkBox_GenApproach";
            this.checkBox_GenApproach.Size = new System.Drawing.Size(72, 17);
            this.checkBox_GenApproach.TabIndex = 32;
            this.checkBox_GenApproach.Text = "Approach";
            this.checkBox_GenApproach.UseVisualStyleBackColor = true;
            // 
            // groupBox_GenerationMode
            // Positioned to the left of the checkboxes column, aligned with them vertically
            // 
            this.groupBox_GenerationMode.Controls.Add(this.radioButton_ModeStrict);
            this.groupBox_GenerationMode.Controls.Add(this.radioButton_ModeLenient);
            this.groupBox_GenerationMode.Location = new System.Drawing.Point(736, 237);
            this.groupBox_GenerationMode.Name = "groupBox_GenerationMode";
            this.groupBox_GenerationMode.Size = new System.Drawing.Size(121, 68);
            this.groupBox_GenerationMode.TabIndex = 33;
            this.groupBox_GenerationMode.TabStop = false;
            this.groupBox_GenerationMode.Text = "Generation Mode";
            // 
            // radioButton_ModeStrict
            // 
            this.radioButton_ModeStrict.AutoSize = true;
            this.radioButton_ModeStrict.Location = new System.Drawing.Point(10, 19);
            this.radioButton_ModeStrict.Name = "radioButton_ModeStrict";
            this.radioButton_ModeStrict.Size = new System.Drawing.Size(49, 17);
            this.radioButton_ModeStrict.TabIndex = 0;
            this.radioButton_ModeStrict.TabStop = true;
            this.radioButton_ModeStrict.Text = "Strict";
            this.radioButton_ModeStrict.UseVisualStyleBackColor = true;
            // 
            // radioButton_ModeLenient
            // 
            this.radioButton_ModeLenient.AutoSize = true;
            this.radioButton_ModeLenient.Location = new System.Drawing.Point(10, 42);
            this.radioButton_ModeLenient.Name = "radioButton_ModeLenient";
            this.radioButton_ModeLenient.Size = new System.Drawing.Size(60, 17);
            this.radioButton_ModeLenient.TabIndex = 1;
            this.radioButton_ModeLenient.TabStop = true;
            this.radioButton_ModeLenient.Text = "Lenient";
            this.radioButton_ModeLenient.UseVisualStyleBackColor = true;
            // 
            // DataSetGeneration
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(6F, 13F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(1183, 606);
            this.Controls.Add(this.groupBox_GenerationMode);
            this.Controls.Add(this.checkBox_GenApproach);
            this.Controls.Add(this.label_VariantCountMulti);
            this.Controls.Add(this.label_VariantCountSingle);
            this.Controls.Add(this.label_VariantCountFloatDouble);
            this.Controls.Add(this.comboBox_VariantCountFloatDouble);
            this.Controls.Add(this.checkBox_GenMultiLevelErrors);
            this.Controls.Add(this.checkBox_GenMultiLevelValueErrors);
            this.Controls.Add(this.checkBox_GenMultiLevelClarification);
            this.Controls.Add(this.checkBox_GenMultiDefaults);
            this.Controls.Add(this.checkBox_GenMultiCommand);
            this.Controls.Add(this.checkBox_GenClarification);
            this.Controls.Add(this.checkBox_GenExtraTypes);
            this.Controls.Add(this.checkBox_GenSingleCommand);
            this.Controls.Add(this.comboBox_VariantCountMulti);
            this.Controls.Add(this.comboBox_VariantCountSingle);
            this.Controls.Add(this.button_Defaults);
            this.Controls.Add(this.checkBox_NumberExpansion);
            this.Controls.Add(this.comboBox_Message);
            this.Controls.Add(this.checkBox_Variations);
            this.Controls.Add(this.button_Restart);
            this.Controls.Add(this.button_GenerateLines);
            this.Controls.Add(this.groupBox_MultiCommand);
            this.Controls.Add(this.label_Message);
            this.Controls.Add(this.comboBox_Type);
            this.Controls.Add(this.label_Type);
            this.Controls.Add(this.groupBox_SingleCommand);
            this.Controls.Add(this.label_Input);
            this.Controls.Add(this.radioButton_Multi);
            this.Controls.Add(this.radioButton_Single);
            this.Controls.Add(this.textBox_Input);
            this.Name = "DataSetGeneration";
            this.Text = "Generate Data Set Lines";
            ((System.ComponentModel.ISupportInitialize)(this.dataGridView_Multi)).EndInit();
            this.groupBox_SingleCommand.ResumeLayout(false);
            this.groupBox_SingleCommand.PerformLayout();
            this.groupBox_MultiCommand.ResumeLayout(false);
            this.groupBox_GenerationMode.ResumeLayout(false);
            this.groupBox_GenerationMode.PerformLayout();
            this.ResumeLayout(false);
            this.PerformLayout();
        }

        #endregion

        private System.Windows.Forms.TextBox textBox_Input;
        private System.Windows.Forms.ComboBox comboBox_SingleParameterKey;
        private System.Windows.Forms.DataGridView dataGridView_Multi;
        private System.Windows.Forms.RadioButton radioButton_Single;
        private System.Windows.Forms.RadioButton radioButton_Multi;
        private System.Windows.Forms.Label label_Input;
        private System.Windows.Forms.GroupBox groupBox_SingleCommand;
        private System.Windows.Forms.ComboBox comboBox_ParameterValueSingle;
        private System.Windows.Forms.Label label_ParameterValueSingle;
        private System.Windows.Forms.Label label_ParameterKeySingle;
        private System.Windows.Forms.Label label_Type;
        private System.Windows.Forms.ComboBox comboBox_Type;
        private System.Windows.Forms.Label label_Message;
        private System.Windows.Forms.GroupBox groupBox_MultiCommand;
        private System.Windows.Forms.DataGridViewCheckBoxColumn ParameterKey;
        private System.Windows.Forms.DataGridViewComboBoxColumn Value;
        private System.Windows.Forms.Button button_GenerateLines;
        private System.Windows.Forms.Button button_Restart;
        private System.Windows.Forms.CheckBox checkBox_Variations;
        private System.Windows.Forms.ComboBox comboBox_Message;
        private System.Windows.Forms.CheckBox checkBox_NumberExpansion;
        private System.Windows.Forms.Button button_Defaults;
        private System.Windows.Forms.ComboBox comboBox_VariantCountSingle;
        private System.Windows.Forms.ComboBox comboBox_VariantCountMulti;
        private System.Windows.Forms.CheckBox checkBox_GenSingleCommand;
        private System.Windows.Forms.CheckBox checkBox_GenExtraTypes;
        private System.Windows.Forms.CheckBox checkBox_GenClarification;
        private System.Windows.Forms.CheckBox checkBox_GenMultiCommand;
        private System.Windows.Forms.CheckBox checkBox_GenMultiDefaults;
        private System.Windows.Forms.CheckBox checkBox_GenMultiLevelClarification;
        private System.Windows.Forms.CheckBox checkBox_GenMultiLevelValueErrors;
        private System.Windows.Forms.CheckBox checkBox_GenMultiLevelErrors;
        private System.Windows.Forms.ComboBox comboBox_VariantCountFloatDouble;
        private System.Windows.Forms.Label label_VariantCountFloatDouble;
        private System.Windows.Forms.Label label_VariantCountSingle;
        private System.Windows.Forms.Label label_VariantCountMulti;
        private System.Windows.Forms.CheckBox checkBox_GenApproach;
        private System.Windows.Forms.GroupBox groupBox_GenerationMode;
        private System.Windows.Forms.RadioButton radioButton_ModeStrict;
        private System.Windows.Forms.RadioButton radioButton_ModeLenient;
    }
}