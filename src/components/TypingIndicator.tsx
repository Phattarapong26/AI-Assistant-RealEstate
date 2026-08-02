import { motion } from "framer-motion";
import { useEffect, useState } from "react";

/**
 * Social-style "is typing…" indicator.
 *
 * Shows three bouncing dots plus a rotating status line so the customer can see
 * which stage of the pipeline the AI is working on (reading, searching the
 * catalogue, running the affordability maths, writing the answer).
 */

const STAGES_TH = [
  "กำลังอ่านคำถามของคุณ",
  "กำลังค้นหาโครงการที่ตรงที่สุด",
  "กำลังคำนวณวงเงินกู้และยอดผ่อน",
  "กำลังเรียบเรียงคำตอบ",
];

const STAGES_EN = [
  "Reading your message",
  "Searching the best matching projects",
  "Estimating your loan and installment",
  "Composing the answer",
];

interface TypingIndicatorProps {
  language?: string;
  avatarSrc?: string;
  name?: string;
}

export default function TypingIndicator({
  language = "th",
  avatarSrc = "/src/image/FundeeDAO.png",
  name = "Property AI Guru",
}: TypingIndicatorProps) {
  const stages = language === "en" ? STAGES_EN : STAGES_TH;
  const [stage, setStage] = useState(0);

  useEffect(() => {
    const id = window.setInterval(
      () => setStage((s) => (s + 1 < stages.length ? s + 1 : s)),
      1600
    );
    return () => window.clearInterval(id);
  }, [stages.length]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.25 }}
      className="chat-message assistant-message"
      aria-live="polite"
      aria-label={stages[stage]}
    >
      <div className="flex items-start">
        <div className="mr-2 flex-shrink-0 rounded-full bg-[#43BE98] p-1">
          <motion.img
            src={avatarSrc}
            alt="AI"
            className="h-8 w-8 rounded-full"
            animate={{ scale: [1, 1.06, 1] }}
            transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
          />
        </div>
        <div className="max-w-[85%]">
          <div className="text-sm font-medium">{name}</div>
          <div className="mt-1 flex items-center gap-3">
            <div className="flex items-center gap-1 rounded-2xl bg-white/80 dark:bg-slate-800/80 px-3 py-2 shadow-sm">
              {[0, 1, 2].map((i) => (
                <motion.span
                  key={i}
                  className="block h-2 w-2 rounded-full bg-[#43BE98]"
                  animate={{ y: [0, -4, 0], opacity: [0.45, 1, 0.45] }}
                  transition={{
                    duration: 0.9,
                    repeat: Infinity,
                    ease: "easeInOut",
                    delay: i * 0.15,
                  }}
                />
              ))}
            </div>
            <motion.span
              key={stage}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25 }}
              className="text-xs text-slate-500 dark:text-slate-300"
            >
              {stages[stage]}…
            </motion.span>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
