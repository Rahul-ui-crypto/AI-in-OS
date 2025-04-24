import React, { useState } from "react";
import Button from "./Button"; // Import the child component

const App = () => {
  const [message, setMessage] = useState("Hello");

  // Function to change message
  const changeMessage = () => {
    setMessage("Hello from Child!");
  };

  return (
    <div>
      <h2>{message}</h2>
      <Button onClick={changeMessage} />
    </div>
  );
};

export default App;
