import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Navbar from "./components/layout/Navbar";
import Home from "./pages/Home";
import UnitCalculator from "./pages/UnitCalculator";
import PFDCanvas from "./pages/PFDCanvas";

// ── Hydrocarbon Recovery Page Component Imports ──────────────────────────────
import HCRecoveryHome from "./pages/hc_recovery/HCRecoveryHome";
import FeedCharacterization from "./pages/hc_recovery/FeedCharacterization";
import Condensation from "./pages/hc_recovery/Condensation";
import Adsorption from "./pages/hc_recovery/Adsorption";
import Membrane from "./pages/hc_recovery/Membrane";
import Comparison from "./pages/hc_recovery/Comparison";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-gray-50">
          <Navbar />
          <Routes>
            {/* Core Platform Routes */}
            <Route path="/"            element={<Home />} />
            <Route path="/calculator"  element={<UnitCalculator />} />
            <Route path="/pfd"         element={<PFDCanvas />} />

            {/* Hydrocarbon Recovery Module Routes */}
            <Route path="/hc-recovery"              element={<HCRecoveryHome />} />
            <Route path="/hc-recovery/feed"         element={<FeedCharacterization />} />
            <Route path="/hc-recovery/condensation" element={<Condensation />} />
            <Route path="/hc-recovery/adsorption"   element={<Adsorption />} />
            <Route path="/hc-recovery/membrane"     element={<Membrane />} />
            <Route path="/hc-recovery/compare"      element={<Comparison />} />
          </Routes>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}