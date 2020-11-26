const ArchiveName = ($filter) => {
  let getNameWithDates = (archive) => {
    return archive.current_version;
  };
  return {
    getNameWithDates: getNameWithDates,
    parseArchiveNames: (archives) => {
      let archiveList = archives.map((archive) => {
        return getNameWithDates(archive);
      });
      return archiveList;
    },
  };
};

export default ArchiveName;
