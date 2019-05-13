const webpack = require('webpack');
const path = require('path');
const CleanWebpackPlugin = require('clean-webpack-plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const ManifestPlugin = require('webpack-manifest-plugin');
const OptimizeCssnanoPlugin = require('@intervolga/optimize-cssnano-plugin');

module.exports = (env, argv) => {
  return {
    entry: './scripts/index.ts',
    output: {
      filename: '[name]-[chunkhash].js',
      path: path.resolve(__dirname, 'build'),
    },
    mode: argv.mode,
    devtool: 'source-map',
    resolve: {
      extensions: ['.ts', '.tsx', '.js', '.jsx'],
    },
    module: {
      rules: [
        {test: /\.tsx?$/, use: 'awesome-typescript-loader'},
        {
          test: /\.js$/,
          include: [
            path.resolve(__dirname, 'scripts'),
            path.resolve(__dirname, 'lang'),
            path.resolve(__dirname, 'node_modules/bufferutil'),
            path.resolve(__dirname, 'node_modules/utf-8-validate'),
          ],
          use: {
            loader: 'babel-loader',
            options: {
              presets: [
                [
                  '@babel/preset-env',
                  {
                    useBuiltIns: 'usage',
                    corejs: 2,
                    modules: false,
                  },
                ],
              ],
              plugins: ['angularjs-annotate'],
            },
          },
        },

        {
          test: /\.(sa|sc|c)ss$/,
          use: [
            {
              loader: MiniCssExtractPlugin.loader,
            },
            {
              loader: 'css-loader',
              options: {
                sourceMap: true,
              },
            },
            {loader: 'postcss-loader', options: {sourceMap: true}},
            'resolve-url-loader',
            {
              loader: 'sass-loader',
              options: {
                sourceMap: true,
                sourceMapContents: false,
              },
            },
          ],
        },
        {
          test: /\.html$/,
          use: [{loader: 'html-loader'}],
        },
        {
          test: path.resolve(__dirname, `scripts/configs/config.json`),
          use: [
            {
              loader: 'ng-package-constants-loader',
              options: {configKey: argv.mode, moduleName: 'essarch.appConfig', wrap: 'es6'},
            },
          ],
          type: 'javascript/auto',
        },
        {
          test: path.resolve(__dirname, 'scripts/configs/permissions.json'),
          use: [
            {
              loader: 'ng-package-constants-loader',
              options: {configKey: 'permissions', moduleName: 'permission.config', wrap: 'es6'},
            },
          ],
          type: 'javascript/auto',
        },
        {test: /\.(png|jpg|gif|svg|woff|woff2)?(\?v=\d+.\d+.\d+)?$/, loader: 'url-loader?limit=8192'},
        {test: /\.(eot|ttf)$/, loader: 'file-loader'},
      ],
    },
    plugins: [
      new webpack.ProvidePlugin({
        $: 'jquery',
        jQuery: 'jquery',
      }),
      new MiniCssExtractPlugin({
        filename: '[name]-[hash].css',
        chunkFilename: '[id]-[hash].css',
      }),
      new ManifestPlugin({fileName: 'rev-manifest.json'}),
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
      new webpack.IgnorePlugin(/^\.\/locale$/, /moment$/),
    ],
    node: {
      fs: 'empty',
      net: 'empty',
      tls: 'empty',
    },
  };
};
