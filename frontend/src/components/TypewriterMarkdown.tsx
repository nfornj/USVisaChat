import { useEffect, useRef, useState } from "react";
import { Box, Link, Stack, Tooltip } from "@mui/material";
import Markdown from "./Markdown";

interface TypewriterMarkdownProps {
  content: string;
  cps?: number; // characters per second
  startDelayMs?: number;
  pauseWhenHidden?: boolean;
  onDone?: () => void;
}

export default function TypewriterMarkdown({
  content,
  cps = 42,
  startDelayMs = 120,
  pauseWhenHidden = true,
  onDone,
}: TypewriterMarkdownProps) {
  const [index, setIndex] = useState(0);
  const [fast, setFast] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const raf = useRef<number | null>(null);
  const last = useRef<number | null>(null);
  const inView = useRef(true);

  // Pause when card not in viewport
  useEffect(() => {
    if (!pauseWhenHidden || !containerRef.current) return;
    const io = new IntersectionObserver(
      (entries) => {
        inView.current = entries[0]?.isIntersecting ?? true;
      },
      { rootMargin: "0px", threshold: 0.05 }
    );
    io.observe(containerRef.current);
    return () => io.disconnect();
  }, [pauseWhenHidden]);

  useEffect(() => {
    let started = false;
    const startAt = performance.now() + startDelayMs;

    const tick = (t: number) => {
      if (index >= content.length) {
        if (raf.current) cancelAnimationFrame(raf.current);
        onDone?.();
        return;
      }
      if (!started && t < startAt) {
        raf.current = requestAnimationFrame(tick);
        return;
      }
      started = true;
      if (pauseWhenHidden && !inView.current) {
        raf.current = requestAnimationFrame(tick);
        return;
      }
      const dt = last.current == null ? 16 : Math.min(100, t - last.current);
      last.current = t;
      const speed = cps * (fast ? 2 : 1);
      let toAdd = Math.max(1, Math.floor((dt * speed) / 1000));

      // Gentle pause after punctuation for readability
      const ch = content[index - 1] || "";
      if (/[\.!?,;:]/.test(ch)) {
        toAdd = Math.max(1, Math.floor(toAdd * 0.6));
      }

      setIndex((i) => Math.min(content.length, i + toAdd));
      raf.current = requestAnimationFrame(tick);
    };

    raf.current = requestAnimationFrame(tick);
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [content, cps, fast, pauseWhenHidden, startDelayMs]);

  const showAll = () => setIndex(content.length);

  return (
    <Box ref={containerRef} onMouseEnter={() => setFast(true)} onMouseLeave={() => setFast(false)}>
      <Box aria-live="polite">
        <Markdown content={content.slice(0, index)} />
      </Box>
      {index < content.length && (
        <Stack direction="row" spacing={1} justifyContent="flex-end">
          <Tooltip title="Skip animation">
            <Link component="button" onClick={showAll} sx={{ fontSize: "0.8rem" }}>
              Show full
            </Link>
          </Tooltip>
        </Stack>
      )}
    </Box>
  );
}
