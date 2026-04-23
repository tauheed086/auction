import confetti from "canvas-confetti";

export const fireCelebration = () => {
  const myConfetti = confetti.create(null, {
    resize: true,
    useWorker: true,
  });

  // LEFT popper 🎉
  myConfetti({
    particleCount: 100,
    angle: 60,
    spread: 80,
    origin: { x: 0, y: 0.6 },
    zIndex: 9999,
  });

  // RIGHT popper 🎉
  myConfetti({
    particleCount: 100,
    angle: 120,
    spread: 80,
    origin: { x: 1, y: 0.6 },
    zIndex: 9999,
  });

  // CENTER BURST
  setTimeout(() => {
    myConfetti({
      particleCount: 200,
      spread: 100,
      origin: { y: 0.5 },
      zIndex: 9999,
    });
  }, 250);
};