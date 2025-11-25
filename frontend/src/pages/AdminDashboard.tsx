import { useEffect, useMemo, useState } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Grid,
  Stack,
  Typography,
  Alert,
} from "@mui/material";
import axios from "axios";
import { useAuth } from "../contexts/AuthContext";

interface MetricsResponse {
  usage: any;
  users: { total_users: number; verified_users: number; active_sessions: number };
  news: { articles: number };
  chat: any;
}

export default function AdminDashboard() {
  const { user } = useAuth();
  const isAdmin = (user?.email || "").toLowerCase() === "nfornj@gmail.com";
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const headers = useMemo(() => ({ "X-Admin-Email": user?.email || "" }), [user]);

  const fetchMetrics = async () => {
    try {
      const res = await axios.get<MetricsResponse>(`/admin/metrics?email=${encodeURIComponent(user?.email || "")}`, { headers });
      setMetrics(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  const forceRefresh = async () => {
    setLoading(true);
    setMessage(null);
    try {
      const res = await axios.post(`/admin/news/force-refresh?email=${encodeURIComponent(user?.email || "")}`, {}, { headers });
      setMessage(res.data?.message || "Triggered refresh");
      await fetchMetrics();
    } catch (e: any) {
      setMessage(e?.response?.data?.detail || "Failed to refresh");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAdmin) fetchMetrics();
  }, [isAdmin]);

  if (!isAdmin) return null;

  const cost = metrics?.usage?.estimated_costs?.total ?? 0;
  const userTotal = metrics?.users?.total_users ?? 0;
  const verified = metrics?.users?.verified_users ?? 0;
  const activeSessions = metrics?.users?.active_sessions ?? 0;
  const newsInDb = metrics?.news?.articles ?? 0;

  return (
    <Box sx={{ p: 3 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h5" fontWeight={700}>Admin Dashboard</Typography>
        <Stack direction="row" spacing={1}>
          <Chip label={`Users: ${metrics?.users?.total_users ?? 0}`} />
          <Chip label={`News in DB: ${metrics?.news?.articles ?? 0}`} />
          <Chip label={`Est. Cost: $${cost.toFixed(2)}`} color="secondary" />
        </Stack>
      </Stack>

      {message && <Alert severity="info" sx={{ mb: 2 }}>{message}</Alert>}

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" fontWeight={700} gutterBottom>Operations</Typography>
              <Button variant="contained" onClick={forceRefresh} disabled={loading}>
                Force Refresh AI News
              </Button>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" fontWeight={700} gutterBottom>Usage</Typography>
              <pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>
                {JSON.stringify(metrics?.usage || {}, null, 2)}
              </pre>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" fontWeight={700} gutterBottom>Stats</Typography>
              <Stack direction="row" spacing={2} flexWrap="wrap">
                <Chip label={`Total Users: ${userTotal}`} />
                <Chip label={`Verified: ${verified}`} />
                <Chip label={`Active Sessions: ${activeSessions}`} />
                <Chip label={`News in DB: ${newsInDb}`} />
                <Chip label={`Est. Cost: $${cost.toFixed(2)}`} color="secondary" />
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
