import { useState, useEffect } from "react";
import {
  Box,
  Card,
  CardContent,
  CardMedia,
  Typography,
  Button,
  Chip,
  CircularProgress,
  Alert,
  Grid,
  Container,
  Stack,
  Fade,
  Switch,
  FormControlLabel,
} from "@mui/material";
import {
  AutoAwesome as AutoAwesomeIcon,
  Schedule as ScheduleIcon,
  Article as ArticleIcon,
  ArrowBack as ArrowBackIcon,
} from "@mui/icons-material";
import TypewriterMarkdown from "./TypewriterMarkdown";


interface NewsArticle {
  id: string;
  title: string;
  summary: string;
  content: string;
  url: string;
  publishedAt: string;
  source: string;
  sources?: { title?: string; url: string; site?: string }[];
  imageUrl?: string;
  aiSummary: string;
  tags: string[];
}

interface AINewsProps {
  onBackToTopics?: () => void;
}


export default function AINews({ onBackToTopics }: AINewsProps) {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState<1 | 2>(1);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [hideYouTube, setHideYouTube] = useState<boolean>(() => {
    try {
      return localStorage.getItem("hideYouTubeEmbeds") === "1";
    } catch {
      return false;
    }
  });

  const fetchNews = async () => {
    setLoading(true);
    setLoadingStep(1);
    setError(null);

    try {
      // Step 1: Searching
      const response = await fetch("/api/ai-news", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: "H1B visa news latest updates 2024",
          limit: 10,
        }),
      });

      // Step 2: Processing (simulated - actual processing happens on backend)
      setLoadingStep(2);

      if (!response.ok) {
        throw new Error("Failed to fetch news");
      }

      const data = await response.json();
      setArticles(data.articles || []);
      // Use the actual cache timestamp from the API response
      if (data.timestamp) {
        setLastUpdated(new Date(data.timestamp));
      } else {
        setLastUpdated(new Date());
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch news");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNews();
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem("hideYouTubeEmbeds", hideYouTube ? "1" : "0");
    } catch {}
  }, [hideYouTube]);

  const getTimeAgo = (dateString: string) => {
    const now = new Date();
    const articleDate = new Date(dateString);
    const diffInHours = Math.floor(
      (now.getTime() - articleDate.getTime()) / (1000 * 60 * 60)
    );

    if (diffInHours < 1) return "Just now";
    if (diffInHours < 24) return `${diffInHours}h ago`;
    const diffInDays = Math.floor(diffInHours / 24);
    return `${diffInDays}d ago`;
  };

  return (
    <Box sx={{ bgcolor: "background.default", minHeight: "100vh", py: 4 }}>
      <Container maxWidth="lg" sx={{ pb: 6 }}>
        {/* Clean Header */}
        <Box sx={{ mb: 5 }}>
          {onBackToTopics && (
            <Button
              startIcon={<ArrowBackIcon />}
              onClick={onBackToTopics}
              sx={{
                mb: 3,
                color: "text.secondary",
                fontWeight: 500,
                "&:hover": { color: "primary.main", bgcolor: "transparent" },
              }}
            >
              Back to Topics
            </Button>
          )}

          <Box sx={{ textAlign: "center", mb: 3 }}>
            <Typography
              variant="h3"
              fontWeight="700"
              sx={{
                mb: 1,
                color: "text.primary",
                fontSize: { xs: "2rem", md: "2.5rem" },
                letterSpacing: "-0.02em",
              }}
            >
              AI News Center
            </Typography>
            <Typography
              variant="body1"
              color="text.secondary"
              sx={{ fontSize: "1.1rem", mb: 2 }}
            >
              Latest H1B visa news powered by AI intelligence
            </Typography>
            <Stack
              direction={{ xs: "column", sm: "row" }}
              spacing={1}
              justifyContent="center"
              alignItems="center"
            >
              <Chip
                icon={<AutoAwesomeIcon sx={{ fontSize: 14 }} />}
                label="AI-Curated"
                size="small"
                sx={{ bgcolor: "background.paper", fontWeight: 500 }}
              />
              {lastUpdated && (
                <Chip
                  icon={<ScheduleIcon sx={{ fontSize: 14 }} />}
                  label={`Last updated ${getTimeAgo(lastUpdated.toISOString())}`}
                  size="small"
                  sx={{ bgcolor: "background.paper", fontWeight: 500 }}
                />
              )}
              <FormControlLabel
                control={
                  <Switch
                    checked={hideYouTube}
                    onChange={(e) => setHideYouTube(e.target.checked)}
                    size="small"
                  />
                }
                label={hideYouTube ? "YouTube: Hidden" : "YouTube: Show"}
                sx={{ ml: { sm: 2 } }}
              />
            </Stack>
          </Box>

          {error && (
            <Alert severity="error" sx={{ mt: 3, borderRadius: 2 }}>
              {error}
            </Alert>
          )}
        </Box>

        {/* Enhanced Loading State with Agent Workflow */}
        {loading && (
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              py: 8,
            }}
          >
            <CircularProgress size={60} thickness={4} />
            
            {/* Step Indicators */}
            <Box sx={{ mt: 4, textAlign: "center" }}>
              {/* Step 1: Searching */}
              <Box sx={{ mb: 3 }}>
                <Stack direction="row" spacing={1} alignItems="center" justifyContent="center">
                  <Box
                    sx={{
                      width: 28,
                      height: 28,
                      borderRadius: "50%",
                      bgcolor: loadingStep >= 1 ? "primary.main" : "action.disabled",
                      color: "white",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "0.875rem",
                      fontWeight: 600,
                    }}
                  >
                    {loadingStep > 1 ? "✓" : "1"}
                  </Box>
                  <Typography
                    variant="body1"
                    sx={{
                      color: loadingStep >= 1 ? "text.primary" : "text.disabled",
                      fontWeight: loadingStep === 1 ? 600 : 400,
                    }}
                  >
                    🔍 Searching for latest H1B news...
                  </Typography>
                </Stack>
              </Box>

              {/* Step 2: Analyzing */}
              <Box>
                <Stack direction="row" spacing={1} alignItems="center" justifyContent="center">
                  <Box
                    sx={{
                      width: 28,
                      height: 28,
                      borderRadius: "50%",
                      bgcolor: loadingStep >= 2 ? "primary.main" : "action.disabled",
                      color: "white",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "0.875rem",
                      fontWeight: 600,
                    }}
                  >
                    2
                  </Box>
                  <Typography
                    variant="body1"
                    sx={{
                      color: loadingStep >= 2 ? "text.primary" : "text.disabled",
                      fontWeight: loadingStep === 2 ? 600 : 400,
                    }}
                  >
                    🤖 Analyzing articles and generating AI summaries...
                  </Typography>
                </Stack>
              </Box>
            </Box>
          </Box>
        )}

        {/* Clean White News Cards */}
        {!loading && articles.length > 0 && (
          <Grid container spacing={4}>
            {articles.map((article, index) => (
              <Grid item xs={12} md={6} key={article.id}>
                <Fade in={true} timeout={200 + index * 50}>
                  <Card
                    elevation={0}
                    sx={{
                      bgcolor: "background.paper",
                      borderRadius: 4,
                      overflow: "hidden",
                      transition: "all 0.3s ease",
                      height: "100%",
                      display: "flex",
                      flexDirection: "column",
                      border: "1px solid",
                      borderColor: "divider",
                      "&:hover": {
                        boxShadow: (theme) => theme.palette.mode === 'dark' 
                          ? "0 8px 24px rgba(0,0,0,0.4)"
                          : "0 8px 24px rgba(0,0,0,0.12)",
                        transform: "translateY(-4px)",
                      },
                    }}
                  >
                    {/* Media: YouTube embed or image */}
                    {(() => {
                      // Avoid embedding YouTube: always skip
                      const ytId = null;
                      if (ytId) {
                        if (hideYouTube) {
                          const thumb = `https://img.youtube.com/vi/${ytId}/hqdefault.jpg`;
                          const watchUrl = `https://www.youtube.com/watch?v=${ytId}`;
                          return (
                            <Box sx={{ position: 'relative' }}>
                              <CardMedia
                                component="img"
                                image={thumb}
                                alt={article.title}
                                sx={{ width: '100%', height: 220, objectFit: 'cover', objectPosition: 'center', filter: 'grayscale(10%)' }}
                              />
                              <Box sx={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: 'rgba(0,0,0,0.35)' }}>
                                <Button variant="contained" color="error" href={watchUrl} target="_blank" rel="noopener noreferrer">
                                  Open on YouTube
                                </Button>
                              </Box>
                            </Box>
                          );
                        }
                        const embedUrl = `https://www.youtube-nocookie.com/embed/${ytId}?rel=0&modestbranding=1`;
                        // Inline player with timeout-based fallback hint
                        return (
                          <Box sx={{ position: 'relative', width: '100%', paddingTop: '56.25%' }}>
                            <iframe
                              src={embedUrl}
                              title={article.title}
                              style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', border: 0 }}
                              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                              sandbox="allow-scripts allow-same-origin allow-presentation"
                              referrerPolicy="no-referrer"
                              allowFullScreen
                              onLoad={(e) => {
                                const overlay = (e.currentTarget.parentElement?.querySelector('[data-yt-overlay]') as HTMLElement) || null;
                                if (overlay) overlay.style.display = 'none';
                              }}
                            />
                            <Box data-yt-overlay sx={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                              <CircularProgress size={28} />
                            </Box>
                            <Box data-yt-fallback sx={{ position: 'absolute', bottom: 8, right: 8, left: 8, display: 'flex', justifyContent: 'flex-end' }}>
                              <Button size="small" href={`https://www.youtube.com/watch?v=${ytId}` } target="_blank" rel="noopener noreferrer" sx={{ bgcolor: 'background.paper' }}>
                                Open on YouTube
                              </Button>
                            </Box>
                          </Box>
                        );
                      }
                      if (article.imageUrl) {
                        return (
                          <CardMedia
                            component="img"
                            image={article.imageUrl}
                            alt={article.title}
                            sx={{
                              width: "100%",
                              height: 220,
                              objectFit: "cover",
                              objectPosition: "center",
                            }}
                          />
                        );
                      }
                      return null;
                    })()}

                    {/* Content */}
                    <CardContent sx={{ p: 3, flexGrow: 1, display: "flex", flexDirection: "column" }}>
                        {/* Title */}
                        <Typography
                          variant="h5"
                          fontWeight="700"
                          sx={{
                            mb: 2,
                            fontSize: "1.4rem",
                            lineHeight: 1.4,
                            color: "text.primary",
                            fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
                            letterSpacing: "-0.01em",
                          }}
                        >
                          {article.title}
                        </Typography>

                        {/* Clean Summary (Markdown) */}
                        <Box sx={{ mb: 2 }}>
<TypewriterMarkdown content={article.aiSummary} cps={48} />
                        </Box>

                        {/* Sources list (inline links) */}
                        <Typography variant="body2" sx={{ mb: 2 }} color="text.secondary">
                          <strong style={{ color: 'inherit' }}>Sources:</strong>{' '}
                          {(
                            (article.sources && article.sources.length > 0
                              ? article.sources
                              : [{ url: article.url }]
                            )
                              .filter((s) => {
                                try {
                                  const host = new URL(s.url).hostname;
                                  return !/youtube\.com|youtu\.be|youtube-nocookie\.com|player\.youtube\.com/i.test(host);
                                } catch { return true; }
                              })
                          )
                            .slice(0, 6)
                            .map((s, i, arr) => {
                              const host = (() => {
                                try { return new URL(s.url).hostname.replace('www.', ''); } catch { return s.url; }
                              })();
                              return (
                                <>
                                  <a
                                    key={s.url + i}
                                    href={s.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={{ color: '#ef4444', textDecoration: 'underline', fontWeight: 700 }}
                                  >
                                    {host}
                                  </a>
                                  {i < arr.length - 1 ? ', ' : ''}
                                </>
                              );
                            })}
                        </Typography>

                        {/* Spacer */}
                        <Box sx={{ flexGrow: 1 }} />

                        {/* Meta */}
                        <Typography variant="caption" color="text.secondary" sx={{ mb: 1 }}>
                          Updated {getTimeAgo(article.publishedAt)}
                        </Typography>

                        {/* Sources chips now replace the old Read More button */}
                      </CardContent>
                  </Card>
                </Fade>
              </Grid>
            ))}
          </Grid>
        )}

        {/* Empty State */}
        {!loading && articles.length === 0 && !error && (
          <Box
            sx={{
              bgcolor: "background.paper",
              textAlign: "center",
              py: 8,
              px: 3,
              borderRadius: 4,
            }}
          >
            <ArticleIcon sx={{ fontSize: 64, color: "text.disabled", mb: 2 }} />
            <Typography variant="h6" color="text.primary" gutterBottom>
              No news articles available
            </Typography>
            <Typography variant="body2" color="text.secondary" mb={3}>
              News will be automatically refreshed every 24 hours
            </Typography>
          </Box>
        )}
      </Container>
    </Box>
  );
}
