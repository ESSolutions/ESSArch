const webpack = require('webpack');
const path = require('path');
const {CleanWebpackPlugin} = require('clean-webpack-plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const ManifestPlugin = require('webpack-manifest-plugin');
const OptimizeCssnanoPlugin = require('@intervolga/optimize-cssnano-plugin');

const basedir = path.resolve(__dirname, 'ESSArch_Core/frontend/static/frontend');

module.exports = (env, argv) => {
  mode = argv.mode || 'development';
  return {
    entry: './ESSArch_Core/frontend/static/frontend/scripts/index.ts',
    resolve: {
      extensions: ['.ts', '.tsx', '.js', '.jsx'],
    },
    optimization: {
      runtimeChunk: 'single',
      splitChunks: {
        cacheGroups: {
          vendor: {
            test: /[\\/]node_modules[\\/]/,
            name: 'vendors',
            chunks: 'all',
          },
        },
      },
    },
    module: {
      rules: [
        {
          test: require.resolve('angular'),
          use: 'imports-loader?$=jquery',
        },
        {
          test: require.resolve('jquery'),
          use: [
            {
              loader: 'expose-loader',
              options: 'jQuery',
            },
            {
              loader: 'expose-loader',
              options: '$',
            },
          ],
        },
        {
          test: /\.tsx?$/,
          use: [
            {
              loader: 'ts-loader',
              options: {
                transpileOnly: true,
                experimentalWatchApi: true,
              },
            },
          ],
        },

        {
          test: /\.js$/,
          include: [path.resolve(basedir, 'scripts'), path.resolve(basedir, 'lang')],
          use: {
            loader: 'babel-loader',
            options: {
              presets: [
                [
                  '@babel/preset-env',
                  {
                    useBuiltIns: 'usage',
                    corejs: 3,
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
            },
          ],
        },
        {
          test: /\.html$/,
          use: [{loader: 'html-loader'}],
        },
        {
          test: path.resolve(basedir, `scripts/configs/config.json`),
          use: [
            {
              loader: 'ng-package-constants-loader',
              options: {configKey: mode, moduleName: 'essarch.appConfig', wrap: 'es6'},
            },
          ],
          type: 'javascript/auto',
        },
        {
          test: path.resolve(basedir, 'scripts/configs/permissions.json'),
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
      new MiniCssExtractPlugin({
        filename: '[name].css',
      }),
      new ManifestPlugin({fileName: 'rev-manifest.json'}),
      new webpack.IgnorePlugin(/^\.\/locale$/, /moment$/),
      new webpack.DefinePlugin({'process.env': {LATER_COV: false}}),
    ],
    node: {
      fs: 'empty',
      net: 'empty',
      tls: 'empty',
    },
  };
};
