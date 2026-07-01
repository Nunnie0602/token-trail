import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom";
import { GameProvider } from "./context/GameContext";
import { GamePage } from "./pages/GamePage";
import { LandingPage } from "./pages/LandingPage";
import { ResultPage } from "./pages/ResultPage";

const router = createBrowserRouter([
  { path: "/", element: <LandingPage /> },
  { path: "/game", element: <GamePage /> },
  { path: "/result/:sessionId?", element: <ResultPage /> },
  { path: "*", element: <Navigate to="/" replace /> },
]);

export default function App() {
  return (
    <GameProvider>
      <RouterProvider router={router} />
    </GameProvider>
  );
}
