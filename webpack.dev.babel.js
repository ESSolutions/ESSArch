const merge = require('webpack-merge');
const common = require('./webpack.common.babel.js');
const path = require('path');
const ForkTsCheckerWebpackPlugin = require('fork-ts-checker-webpack-plugin');

const basedir = path.resolve(__dirname, 'ESSArch_Core/frontend/static/frontend');

module.exports = (env, argv) => {
  return merge(common(env, argv), {
    mode: 'development',
    devtool: 'cheap-module-eval-source-map',
    output: {
      filename: '[name].js',
      path: path.resolve(basedir, 'build'),
    },
    plugins: [new ForkTsCheckerWebpackPlugin()],
  });
};
