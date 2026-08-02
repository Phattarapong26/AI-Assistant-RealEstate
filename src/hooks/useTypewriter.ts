import { useEffect, useRef, useState } from "react";

/**
 * Reveals text progressively so a completed answer still feels like it is being
 * typed live. Typing speed is character-based and skips instantly when the
 * caller disables the effect (e.g. when replaying chat history).
 */
export function useTypewriter(
  text: string,
  enabled: boolean,
  options?: { charsPerTick?: number; tickMs?: number; onUpdate?: () => void }
) {
  // Long, guru-length answers should still finish in a few seconds, so the
  // reveal rate scales with the length of the message.
  const adaptiveChars = Math.max(3, Math.ceil(text.length / 260));
  const { charsPerTick = adaptiveChars, tickMs = 16, onUpdate } = options ?? {};
  const [visible, setVisible] = useState(enabled ? "" : text);
  const updateRef = useRef(onUpdate);
  updateRef.current = onUpdate;

  useEffect(() => {
    if (!enabled) {
      setVisible(text);
      return;
    }
    setVisible("");
    let index = 0;
    const id = window.setInterval(() => {
      index = Math.min(index + charsPerTick, text.length);
      setVisible(text.slice(0, index));
      updateRef.current?.();
      if (index >= text.length) window.clearInterval(id);
    }, tickMs);
    return () => window.clearInterval(id);
  }, [text, enabled, charsPerTick, tickMs]);

  return { visible, isTyping: enabled && visible.length < text.length };
}

export default useTypewriter;
