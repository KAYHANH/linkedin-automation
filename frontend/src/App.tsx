import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { DashboardLayout } from "./layouts/DashboardLayout";
import { LoginPage } from "./pages/LoginPage";
import { OverviewPage } from "./pages/OverviewPage";
import { CalendarPage } from "./pages/CalendarPage";
import { DraftsPage } from "./pages/DraftsPage";
import { NewPostPage } from "./pages/NewPostPage";
import { DraftEditorPage } from "./pages/DraftEditorPage";
import { ResearchPage } from "./pages/ResearchPage";
import { StrategyPage } from "./pages/StrategyPage";
import { HistoryPage } from "./pages/HistoryPage";
import { LogsPage } from "./pages/LogsPage";
import { SettingsPage } from "./pages/SettingsPage";

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<DashboardLayout />}>
          <Route index element={<OverviewPage />} />
          <Route path="calendar" element={<CalendarPage />} />
          <Route path="drafts" element={<DraftsPage />} />
          <Route path="new-post" element={<NewPostPage />} />
          <Route path="editor/:date" element={<DraftEditorPage />} />
          <Route path="research" element={<ResearchPage />} />
          <Route path="strategy" element={<StrategyPage />} />
          <Route path="history" element={<HistoryPage />} />
          <Route path="logs" element={<LogsPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
};
