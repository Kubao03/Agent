export type Model = {
  id:    string;
  label: string;
};

export const MODELS: Model[] = [
  { id: "deepseek-chat",     label: "DeepSeek" },
  { id: "gemini-3-flash",    label: "Gemini"   },
  { id: "qwen-plus",         label: "Qwen"     },
  { id: "claude-sonnet-4-6", label: "Claude"   },
];
