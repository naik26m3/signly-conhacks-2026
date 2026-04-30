const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);

// Limit transform workers on Windows to avoid SIGTERM crashes under memory pressure
config.maxWorkers = 2;

module.exports = config;
