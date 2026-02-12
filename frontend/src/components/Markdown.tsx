import ReactMarkdown from "react-markdown";
import { Typography } from "@mui/material";

interface MarkdownProps {
  content: string;
}

// Normalize AI text to proper Markdown (e.g., convert • bullets to '-')
function normalizeMarkdown(text: string): string {
  let t = text || "";
  // Convert Windows/Mac newlines to \n
  t = t.replace(/\r\n?/g, "\n");
  // Convert bullet characters at line start to markdown dashes
  t = t.replace(/^\s*[•▪︎●]\s+/gm, "- ");
  // Ensure headings with trailing ':' render bold as intended
  // (keep as-is; bold is already **text** from backend)
  return t.trim();
}

export default function Markdown({ content }: MarkdownProps) {
  const md = normalizeMarkdown(content);
  return (
    <ReactMarkdown
      components={{
        p: ({ children }) => (
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ mb: 1.5, lineHeight: 1.7, fontSize: "0.95rem" }}
          >
            {children}
          </Typography>
        ),
        strong: ({ children }) => (
          <Typography component="span" fontWeight={700} color="primary.dark">
            {children}
          </Typography>
        ),
        em: ({ children }) => (
          <Typography component="span" fontStyle="italic">
            {children}
          </Typography>
        ),
        ul: ({ children }) => (
          <ul style={{ paddingLeft: 20, marginTop: 4, marginBottom: 12 }}>{children}</ul>
        ),
        li: ({ children }) => <li style={{ marginBottom: 6 }}>{children}</li>,
      }}
    >
      {md}
    </ReactMarkdown>
  );
}