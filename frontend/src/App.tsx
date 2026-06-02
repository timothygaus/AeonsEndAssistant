import { BrowserRouter, Routes, Route } from "react-router-dom"
import Home from "./pages/Home"
import SetSelection from "./pages/SetSelection"
import Quickplay from "./pages/Quickplay"
import ExpeditionMode from "./pages/ExpeditionMode"
import ExpeditionView from "./pages/ExpeditionView"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import NewExpedition from "./pages/NewExpedition"
import ExpeditionResume from "./pages/ExpeditionResume"

const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path='/' element={<Home />} />
          <Route path='/sets' element={<SetSelection />} />
          <Route path='/quickplay' element={<Quickplay />} />
          <Route path='/expedition' element={<ExpeditionMode />} />
          <Route path='/expedition/:id' element={<ExpeditionView />} />
          <Route path='/expedition/new' element={<NewExpedition />} />
          <Route path='/expedition/resume' element={<ExpeditionResume />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App