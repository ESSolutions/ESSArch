const presetEnv = require('postcss-preset-env');
const autoprefixer = require('autoprefixer');

module.exports = {
  plugins: [autoprefixer, presetEnv],
};
