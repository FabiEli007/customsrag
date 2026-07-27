import { useState, type FormEvent } from "react";
import { Icon } from "./Icon";

interface QuestionInputProps {
  onSubmit: (question: string) => void;
  disabled: boolean;
  placeholder: string;
  submitLabel: string;
}

export function QuestionInput({ onSubmit, disabled, placeholder, submitLabel }: QuestionInputProps) {
  const [value, setValue] = useState("");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setValue("");
  }

  return (
    <form
      className="flex items-center gap-2 border-t border-outline-variant bg-surface-container-low px-4 py-3"
      onSubmit={handleSubmit}
    >
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        aria-label={placeholder}
        className="flex-1 rounded border border-outline-variant bg-surface-container-lowest px-3 py-2.5 text-sm text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:border-primary focus:border-2"
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className="flex items-center gap-1.5 rounded bg-primary text-on-primary px-4 py-2.5 text-sm font-semibold disabled:bg-outline disabled:cursor-not-allowed hover:bg-primary-container transition-colors"
      >
        <Icon name="send" className="text-[18px]" />
        <span className="hidden sm:inline">{submitLabel}</span>
      </button>
    </form>
  );
}
