class MyAudioProcessor extends AudioWorkletProcessor {
    constructor() {
      super();
    }
  
    process(inputs, outputs, parameters) {
      const input = inputs[0];
      const output = outputs[0];
  
      // Assuming mono audio (1 channel)
      if (input.length > 0 && output.length > 0) {
        const inputData = input[0];
        const outputData = output[0];
  
        // If you want to use inputData after posting it, make a copy before posting.
        const inputDataCopy = inputData.slice();
  
        // Pass the audio data to the main thread
        this.port.postMessage(inputDataCopy);
  
        // Copy the input data to the output array to play the audio
        // outputData.set(inputData);
      }
  
      return true; // Keep the processor alive
    }
  }
  
  registerProcessor('audio-processor', MyAudioProcessor);