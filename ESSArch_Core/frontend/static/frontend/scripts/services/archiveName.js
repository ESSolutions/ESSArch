const ArchiveName = $filter => {
  let getNameWithDates = archive => {
    archive.current_version.name_with_dates =
      archive.current_version.name +
      (archive.current_version.start_date !== null || archive.current_version.end_date != null
        ? ' (' +
          (archive.current_version.start_date !== null
            ? $filter('date')(archive.current_version.start_date, 'yyyy')
            : '') +
          ' - ' +
          (archive.current_version.end_date !== null
            ? $filter('date')(archive.current_version.end_date, 'yyyy')
            : '') +
          ')'
        : '');
    return archive.current_version;
  };
  return {
    getNameWithDates: getNameWithDates,
    parseArchiveNames: archives => {
      let archiveList = archives.map(archive => {
        return getNameWithDates(archive);
      });
      return archiveList;
    },
  };
};

export default ArchiveName;
