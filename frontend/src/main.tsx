import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, StrictMode, Suspense } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, Navigate, RouterProvider } from "react-router";

import { AuthProvider } from "./auth/AuthProvider";
import { AppShell } from "./components/AppShell";
import { RequireAuth } from "./components/RequireAuth";
import { Spinner } from "./components/ui";
import "./styles.css";

const DashboardPage = lazy(() =>
  import("./pages/DashboardPage").then((module) => ({
    default: module.DashboardPage,
  })),
);
const AthenaeumPage = lazy(() =>
  import("./pages/AthenaeumPage").then((module) => ({
    default: module.AthenaeumPage,
  })),
);
const GrimoirePage = lazy(() =>
  import("./pages/GrimoirePage").then((module) => ({
    default: module.GrimoirePage,
  })),
);
const LoginPage = lazy(() =>
  import("./pages/LoginPage").then((module) => ({ default: module.LoginPage })),
);

function RouteFallback() {
  return (
    <div className="boot-screen">
      <Spinner label="Opening the library…" />
    </div>
  );
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 20_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const router = createBrowserRouter([
  {
    path: "/login",
    element: (
      <Suspense fallback={<RouteFallback />}>
        <LoginPage />
      </Suspense>
    ),
  },
  {
    path: "/",
    element: (
      <RequireAuth>
        <AppShell />
      </RequireAuth>
    ),
    children: [
      {
        index: true,
        element: (
          <Suspense fallback={<RouteFallback />}>
            <DashboardPage />
          </Suspense>
        ),
      },
      {
        path: "a/:athenaeumId",
        element: (
          <Suspense fallback={<RouteFallback />}>
            <AthenaeumPage />
          </Suspense>
        ),
      },
      {
        path: "g/:grimoireId",
        element: (
          <Suspense fallback={<RouteFallback />}>
            <GrimoirePage />
          </Suspense>
        ),
      },
      {
        path: "g/:grimoireId/n/:nodeId",
        element: (
          <Suspense fallback={<RouteFallback />}>
            <GrimoirePage />
          </Suspense>
        ),
      },
    ],
  },
  { path: "*", element: <Navigate to="/" replace /> },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>,
);
