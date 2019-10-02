import * as moment from 'moment';

import 'moment/locale/sv.js';

export default class LanguageCtrl {
  appConfig: any;
  http: ng.IHttpService;
  translate: ng.translate.ITranslateService;
  currentLanguage: string | null;
  availableLanguages: string[];

  constructor(appConfig, $http, $translate) {
    this.appConfig = appConfig;
    this.http = $http;
    this.translate = $translate;

    this.currentLanguage = null;
    this.availableLanguages = [];
  }

  setUserLanguage(lang: string) {
    return this.http({
      method: 'PATCH',
      url: this.appConfig.djangoUrl + 'me/',
      data: {
        language: lang,
      },
    }).then(function(response) {
      return response;
    });
  }

  getUserLanguage() {
    return this.http({
      method: 'GET',
      url: this.appConfig.djangoUrl + 'me/',
    }).then(function(response: ng.IHttpResponse<{language: string}>) {
      return response.data.language;
    });
  }

  changeLanguage(lang: string) {
    this.setUserLanguage(lang);
    this.currentLanguage = lang;
    this.translate.use(lang);
    moment.locale(lang);
  }

  getCurrentLanguage() {
    this.getUserLanguage().then(apiLang => {
      this.changeLanguage(apiLang);
    });
  }

  $onInit() {
    this.getCurrentLanguage();
    this.loadLanguages();
  }

  loadLanguages() {
    this.availableLanguages = this.translate.getAvailableLanguageKeys();
  }
}
