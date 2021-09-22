const {merge} = require('webpack-merge');
const common = require('./webpack.common.babel.js');
const path = require('path');

const {CleanWebpackPlugin} = require('clean-webpack-plugin');
const TerserPlugin = require('terser-webpack-plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const CssMinimizerPlugin = require('css-minimizer-webpack-plugin');
const ForkTsCheckerWebpackPlugin = require('fork-ts-checker-webpack-plugin');

const basedir = path.resolve(__dirname, 'ESSArch_Core/frontend/static/frontend');

module.exports = (env, argv) => {
  return merge(common(env, argv), {
    mode: 'production',
    devtool: 'source-map',
    output: {
      filename: '[name]-[chunkhash].js',
      path: path.resolve(basedir, 'build'),
    },
    optimization: {
      minimizer: [
        new TerserPlugin({
          terserOptions: {
            compress: {
              drop_console: true,
            },
          },
        }),
        new CssMinimizerPlugin({
          minimizerOptions: {
            preset: [
              'default',
              {
                discardComments: {removeAll: true},
              },
            ],
          },
        }),
      ],
    },
    plugins: [
      new ForkTsCheckerWebpackPlugin(),
      new MiniCssExtractPlugin({
        filename: '[name]-[chunkhash].css',
        chunkFilename: '[id]-[chunkhash].css',
      }),
      new CleanWebpackPlugin(),
    ],
  });
};
