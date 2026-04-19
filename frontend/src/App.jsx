import { useState } from 'react';
import Locker from './components/Locker';
import Results from './components/Results'; // You'll make this next
import './index.css';

function App() {
  const [showResults, setShowResults] = useState(false);

  return (
    <div className="App">
      {!showResults ? (
        // Pass the "Trigger" function to the Locker
        <Locker onNavigate={() => setShowResults(true)} />
      ) : (
        <Results onBack={() => setShowResults(false)} />
      )}
    </div>
  );
}

export default App;