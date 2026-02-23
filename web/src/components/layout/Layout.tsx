import { Outlet } from "react-router-dom";
import { Header } from "./Header";

export function Layout() {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-6">
        <Outlet />
      </main>
      <footer className="border-t border-surface-border py-4 text-center text-xs text-gray-500">
        Metalcore Index &middot; AI-powered industry intelligence
      </footer>
    </div>
  );
}
