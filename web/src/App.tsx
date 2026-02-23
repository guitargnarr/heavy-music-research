import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "./components/layout/Layout";
import { DashboardPage } from "./pages/DashboardPage";
import { ArtistDetailPage } from "./pages/ArtistDetailPage";
import { NetworkPage } from "./pages/NetworkPage";
import { AboutPage } from "./pages/AboutPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/artist/:id" element={<ArtistDetailPage />} />
          <Route path="/network" element={<NetworkPage />} />
          <Route path="/about" element={<AboutPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
