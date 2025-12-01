const webpack = require('webpack');
const path = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const {WebpackManifestPlugin} = require('webpack-manifest-plugin');
const {GitRevisionPlugin} = require('git-revision-webpack-plugin');
const gitRevisionPlugin = new GitRevisionPlugin();

const basedir = path.resolve(__dirname, 'ESSArch_Core/frontend/static/frontend');

module.exports = (env, argv) => {
  const mode = argv.mode || 'development';
  const isProd = mode === 'production';

  return {
    mode,

    entry: './ESSArch_Core/frontend/static/frontend/scripts/index.ts',

    resolve: {
      extensions: ['.ts', '.tsx', '.js', '.jsx'],
      fallback: {
        fs: false,
        net: false,
        tls: false,
        url: false,
        path: require.resolve('path-browserify'),
        os: require.resolve('os-browserify/browser'),
        util: require.resolve('util/'),
        zlib: require.resolve('browserify-zlib'),
        crypto: require.resolve('crypto-browserify'),
        http: require.resolve('stream-http'),
        https: require.resolve('https-browserify'),
        stream: require.resolve('stream-browserify'),
        assert: require.resolve('assert/'),
        buffer: require.resolve('buffer/'),
      },
    },

    optimization: {
      runtimeChunk: 'single',
      splitChunks: {
        cacheGroups: {
          default: false,
          vendors: {
            name: 'vendors',
            chunks: 'all',
            enforce: true,
            test(module) {
              const resource = module.resource || '';
              if (resource.includes('node_modules') && resource.includes('@uppy')) {
                return false; // exclude Uppy from vendors
              }
              return /[\\/]node_modules[\\/]/.test(resource);
            },
          },
        },
      },
    },

    module: {
      rules: [
        // Angular + jQuery
        {
          test: require.resolve('angular'),
          use: [
            {
              loader: 'imports-loader',
              options: {type: 'commonjs', imports: {moduleName: 'jquery', name: '$'}},
            },
          ],
        },
        {
          test: require.resolve('jquery'),
          use: [
            {loader: 'expose-loader', options: {exposes: {globalName: 'jQuery'}}},
            {loader: 'expose-loader', options: {exposes: {globalName: '$'}}},
          ],
        },

        // TypeScript
        {
          test: /\.tsx?$/,
          use: {loader: 'ts-loader', options: {transpileOnly: true, experimentalWatchApi: true}},
        },

        // JS via Babel
        {
          test: /\.js$/,
          include: [path.resolve(basedir, 'scripts'), path.resolve(basedir, 'lang')],
          use: {
            loader: 'babel-loader',
            options: {
              presets: [
                ['@babel/preset-env', {useBuiltIns: 'usage', corejs: 3, modules: false}],
                '@babel/preset-react',
              ],
              plugins: ['angularjs-annotate'],
            },
          },
        },

        // CSS / SCSS
        {
          test: /\.(sa|sc|c)ss$/,
          use: [
            {loader: MiniCssExtractPlugin.loader, options: {publicPath: ''}},
            'css-loader',
            'postcss-loader',
            'resolve-url-loader',
            'sass-loader',
          ],
        },

        // HTML templates
        {test: /\.html$/, use: ['html-loader']},

        // JSON for Angular configs
        {
          test: path.resolve(basedir, 'scripts/configs/config.json'),
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

        // Assets
        {
          test: /\.(png|jpg|gif|svg|ico|eot|ttf|woff|woff2)(\?.*)?$/,
          type: 'asset/resource',
          generator: {filename: 'assets/[hash][ext]'},
        },
      ],
    },

    plugins: [
      new MiniCssExtractPlugin({filename: '[name].css'}),
      new WebpackManifestPlugin({fileName: 'rev-manifest.json', publicPath: ''}),
      new webpack.IgnorePlugin({resourceRegExp: /^\.\/locale$/, contextRegExp: /moment$/}),
      new webpack.DefinePlugin({
        'process.env': {LATER_COV: false},
        COMMITHASH: JSON.stringify(gitRevisionPlugin.commithash()),
      }),
      new webpack.ProvidePlugin({Buffer: ['buffer', 'Buffer']}),
    ],
  };
};
