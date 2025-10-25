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
  IconButton,
  Stack,
  Fade,
} from "@mui/material";
import {
  OpenInNew as OpenInNewIcon,
  Refresh as RefreshIcon,
  AutoAwesome as AutoAwesomeIcon,
  Schedule as ScheduleIcon,
  Article as ArticleIcon,
  ArrowBack as ArrowBackIcon,
} from "@mui/icons-material";


interface NewsArticle {
  id: string;
  title: string;
  summary: string;
  content: string;
  url: string;
  publishedAt: string;
  source: string;
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
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchNews = async () => {
    setLoading(true);
    setError(null);

    try {
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
      <Container maxWidth="lg">
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
              direction="row"
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
                  label={`Updated ${getTimeAgo(lastUpdated.toISOString())}`}
                  size="small"
                  sx={{ bgcolor: "background.paper", fontWeight: 500 }}
                />
              )}
              <IconButton
                onClick={fetchNews}
                disabled={loading}
                size="small"
                sx={{
                  bgcolor: "primary.main",
                  color: "white",
                  width: 32,
                  height: 32,
                  "&:hover": {
                    bgcolor: "primary.dark",
                  },
                  "&:disabled": {
                    bgcolor: "action.disabledBackground",
                  },
                }}
              >
                <RefreshIcon fontSize="small" />
              </IconButton>
            </Stack>
          </Box>

          {error && (
            <Alert severity="error" sx={{ mt: 3, borderRadius: 2 }}>
              {error}
            </Alert>
          )}
        </Box>

        {/* Loading State */}
        {loading && (
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              py: 8,
            }}
          >
            <CircularProgress size={50} thickness={4} />
            <Typography variant="body1" color="text.secondary" sx={{ mt: 3 }}>
              Fetching latest H1B news from Perplexity...
            </Typography>
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
                    {/* Hero Image */}
                    {article.imageUrl && (
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
                    )}

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

                        {/* Clean Summary */}
                        <Typography
                          variant="body2"
                          color="text.secondary"
                          sx={{
                            mb: 3,
                            lineHeight: 1.7,
                            fontSize: "0.95rem",
                            whiteSpace: "pre-line",
                          }}
                        >
                          {article.aiSummary}
                        </Typography>

                        {/* Spacer */}
                        <Box sx={{ flexGrow: 1 }} />

                        {/* Bottom Section */}
                        <Stack direction="row" spacing={1} alignItems="center" mb={2}>
                          <Chip
                            label={article.source}
                            size="small"
                            sx={{
                              bgcolor: (theme) => theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.08)' : '#f0f0f0',
                              color: "text.secondary",
                              fontWeight: 500,
                              fontSize: "0.75rem",
                            }}
                          />
                          <Typography variant="caption" color="text.secondary">
                            • {getTimeAgo(article.publishedAt)}
                          </Typography>
                        </Stack>

                        {/* Action button */}
                        <Button
                          variant="text"
                          endIcon={<OpenInNewIcon fontSize="small" />}
                          href={article.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          fullWidth
                          sx={{
                            textTransform: "none",
                            fontWeight: 600,
                            justifyContent: "space-between",
                            color: "primary.main",
                            "&:hover": {
                              bgcolor: "rgba(25, 118, 210, 0.04)",
                            },
                          }}
                        >
                          Read More
                        </Button>
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
              Click the refresh button to fetch the latest H1B visa news
            </Typography>
            <Button
              variant="contained"
              startIcon={<RefreshIcon />}
              onClick={fetchNews}
            >
              Refresh News
            </Button>
          </Box>
        )}
      </Container>
    </Box>
  );
}
