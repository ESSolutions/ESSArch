/*@ngInject*/
export default $translateProvider => {
  $translateProvider.translations('sv', {
    ERROR: {
      ERROR: 'Fel',
      CONNECTION_LOST: 'Anslutning förlorad',
      CONNECTION_RESTORED: 'Anslutning återupprättad',
      ERROR_403: 'Du har inte rätt att utföra denna åtgärd',
      ERROR_500: 'Internt serverfel',
      ERROR_503: 'Förfrågan misslyckades, försök igen',
      RETRY_CONNECTION: 'Försök igen',
      UNKNOWN_ERROR: 'Okänt fel',
    },
  });
};
