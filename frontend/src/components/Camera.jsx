// src/components/Camera.jsx
import { useState } from 'react';
import { animate, stagger } from 'animejs'; 
import cameraImg from '../assets/final_camera1.png';
import sayImg from '../assets/final_say.png';
import cheeseImg from '../assets/final_cheese.png';

const Camera = ({ onCapture }) => {
  const [isPhotoTaken, setIsPhotoTaken] = useState(false);

  // Helper function for that "touch" feel
  const playBounce = (target) => {
    animate(target, {
      scale: [1, 1.15, 1],
      duration: 300,
      easing: 'easeOutElastic(1, .6)'
    });
  };

  const handleCapture = () => {
    setIsPhotoTaken(true);

    // Camera body squish
    animate('.digicam-body', {
      scale: [1, 0.95, 1],
      duration: 150,
      easing: 'easeInOutQuad' 
    });

    // Text "Pop" animation
    animate(['.say-text', '.cheese-text'], {
      scale: [1, 1.4, 1],
      rotate: [0, 10, -10, 0],
      duration: 600,
      delay: stagger(60),
      easing: 'easeOutElastic(1, .5)'
    });

    setTimeout(() => setIsPhotoTaken(false), 2000);
  };

  return (
    <div className="camera-wrapper" style={{ 
      position: 'absolute', 
      top: '100px', 
      left: '50px', 
      width: '1000px',
      zIndex: 20 
    }}>
      
      {/* Say Image - Visible initially, pops on click */}
      <img 
        src={sayImg} 
        className="say-text" 
        onClick={(e) => playBounce(e.currentTarget)}
        style={{ 
          opacity: 1, 
          position: 'absolute', 
          top: '-10px', 
          left: '150px', 
          width: '100px',
          cursor: 'pointer'
        }} 
      />

      {/* Cheese Image - Visible initially, pops on click */}
      <img 
        src={cheeseImg} 
        className="cheese-text" 
        onClick={(e) => playBounce(e.currentTarget)}
        style={{ 
          opacity: 1, 
          position: 'absolute', 
          top: '10px', 
          left: '220px', 
          width: '200px',
          cursor: 'pointer'
        }} 
      />

      {/* Shutter Button */}
      <button
        onClick={() => {
          handleCapture();
          setTimeout(() => {
            if (onCapture) onCapture();
          }, 350); // Slight delay so they see the animation before switching
        }}
        style={{
          position: 'absolute',
          top: '290px',
          left: '688px',
          width: '50px',
          height: '50px',
          borderRadius: '50%',
          backgroundColor: '#ffffff',
          border: '3px solid #ddd',
          cursor: 'pointer',
          boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
          zIndex: 50,
          transition: 'transform 0.1s'
        }}
        onMouseDown={(e) => e.currentTarget.style.transform = 'scale(0.9)'}
        onMouseUp={(e) => e.currentTarget.style.transform = 'scale(1)'}
      />

      <img 
        src={cameraImg} 
        className="digicam-body" 
        style={{ width: '900px', display: 'block' }} 
      />
    </div>
  );
};

export default Camera;