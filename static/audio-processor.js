class AudioProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this.chunkSize = 1600; // 100ms at 16kHz
        this.buffer = new Int16Array(this.chunkSize);
        this.bufferIndex = 0;
    }

    process(inputs, outputs, parameters) {
        const input = inputs[0];
        if (input && input.length > 0) {
            const channel = input[0];
            for (let i = 0; i < channel.length; i++) {
                let s = Math.max(-1, Math.min(1, channel[i]));
                s = s < 0 ? s * 0x8000 : s * 0x7FFF;
                this.buffer[this.bufferIndex++] = s;
                if (this.bufferIndex >= this.chunkSize) {
                    this.port.postMessage(this.buffer.buffer.slice(0), [this.buffer.buffer.slice(0)]);
                    this.bufferIndex = 0;
                }
            }
        }
        return true;
    }
}

registerProcessor('audio-processor', AudioProcessor);
