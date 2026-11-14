// Same-origin worker wrapper. The matching Stockfish WASM file is fetched from jsDelivr.
const engineBase = "https://cdn.jsdelivr.net/npm/stockfish@19.0.1/bin/";
self.Module = {
    locateFile: function (path) {
        return engineBase + path;
    }
};
importScripts(engineBase + "stockfish-19-lite-single.js");
