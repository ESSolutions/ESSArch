const merge = require('webpack-merge');
const common = require('./webpack.common.babel.js');
const path = require('path');

const {CleanWebpackPlugin} = require('clean-webpack-plugin');
const TerserPlugin = require('terser-webpack-plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const OptimizeCssnanoPlugin = require('@intervolga/optimize-cssnano-plugin');
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
          sourceMap: true,
          terserOptions: {
            compress: {
              drop_console: true,
            },
          },
        }),
      ],
    },
    plugins: [
      new ForkTsCheckerWebpackPlugin(),
      new MiniCssExtractPlugin({
        filename: '[name]-[hash].css',
        chunkFilename: '[id]-[hash].css',
      }),
      new CleanWebpackPlugin(),
      new OptimizeCssnanoPlugin({
        sourceMap: true,
        cssnanoOptions: {
          preset: [
            'default',
            {
              discardComments: {
                removeAll: true,
              },
            },
          ],
        },
      }),
    ],
  });
};
