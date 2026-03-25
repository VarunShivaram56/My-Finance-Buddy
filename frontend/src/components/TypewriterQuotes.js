import { useEffect, useState } from "react";

const QUOTES = [
  "Welcome to your personal finance companion.",
  "A private space to understand and manage your money.",
  "Turn bank statements into clear financial stories.",
  "Smarter finance starts with better understanding.",
];

const TYPING_SPEED = 45;
const HOLD_DURATION = 1500;
const DELETING_SPEED = 20;

function TypewriterQuotes() {
  const [quoteIndex, setQuoteIndex] = useState(0);
  const [displayText, setDisplayText] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    const currentQuote = QUOTES[quoteIndex];
    const isComplete = displayText === currentQuote;
    const isEmpty = displayText.length === 0;

    let timeout;

    if (!isDeleting && !isComplete) {
      timeout = setTimeout(() => {
        setDisplayText(currentQuote.slice(0, displayText.length + 1));
      }, TYPING_SPEED);
    } else if (!isDeleting && isComplete) {
      timeout = setTimeout(() => setIsDeleting(true), HOLD_DURATION);
    } else if (isDeleting && !isEmpty) {
      timeout = setTimeout(() => {
        setDisplayText(currentQuote.slice(0, displayText.length - 1));
      }, DELETING_SPEED);
    } else {
      setIsDeleting(false);
      setQuoteIndex((prev) => (prev + 1) % QUOTES.length);
    }

    return () => clearTimeout(timeout);
  }, [displayText, isDeleting, quoteIndex]);

  return (
    <p className="typewriter-caret min-h-16 max-w-2xl text-center text-lg text-slate-600 sm:text-xl">
      {displayText}
    </p>
  );
}

export default TypewriterQuotes;
