// Try two independent package CDNs so a temporary outage on one does not
// prevent the Stockfish worker from starting.
const engineFile = "stockfish-19-lite-single.js";
const engineBases = [
    "https://unpkg.com/stockfish@19.0.1/bin/",
    "https://cdn.jsdelivr.net/npm/stockfish@19.0.1/bin/"
];

let loaded = false;
let lastError = null;

for (const engineBase of engineBases) {
    self.Module = {
        locateFile: function (path) {
            return engineBase + path;
        }
    };

    try {
        importScripts(engineBase + engineFile);
        loaded = true;
        break;
    } catch (error) {
        lastError = error;
    }
}

if (!loaded) {
    throw new Error("Could not load Stockfish from either CDN: " + lastError);
}
