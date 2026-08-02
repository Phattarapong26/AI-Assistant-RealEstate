import { motion } from "framer-motion";
import { useTypewriter } from "@/hooks/useTypewriter";

interface AnimatedAnswerProps {
  text: string;
  animate: boolean;
  onTick?: () => void;
}

/**
 * Assistant answer body. While the answer is being revealed a soft caret blinks
 * at the end of the text, matching the "friend is typing" feel of social chat.
 */
export default function AnimatedAnswer({ text, animate, onTick }: AnimatedAnswerProps) {
  const { visible, isTyping } = useTypewriter(text, animate, { onUpdate: onTick });

  return (
    <div className="mt-1 whitespace-pre-line leading-relaxed">
      {visible}
      {isTyping && (
        <motion.span
          className="ml-0.5 inline-block h-4 w-[2px] translate-y-[2px] bg-[#43BE98]"
          animate={{ opacity: [1, 0.15, 1] }}
          transition={{ duration: 0.8, repeat: Infinity }}
        />
      )}
    </div>
  );
}
