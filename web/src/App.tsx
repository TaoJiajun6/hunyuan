import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import IndexPage from './pages/IndexPage';
import PodcastPage from './pages/PodcastPage';
import MultiRolePage from './pages/podcast/MultiRolePage';
import CharacterPage from './pages/podcast/CharacterPage';
import DeepPage from './pages/podcast/DeepPage';
import StreamingScriptPage from './pages/podcast/StreamingScriptPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<IndexPage />}>
          <Route index element={<Navigate to="/podcast" replace />} />
          <Route path="podcast" element={<PodcastPage />} />
          <Route path="podcast/multi-role" element={<MultiRolePage />} />
          <Route path="podcast/character" element={<CharacterPage />} />
          <Route path="podcast/deep" element={<DeepPage />} />
          <Route path="podcast/streaming-script" element={<StreamingScriptPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;

