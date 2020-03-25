const StructureName = ($filter, $translate) => {
  function getNameWithVersion(structure) {
    const versionTestructuret = $translate.instant('VERSION');
    return (
      structure.name +
      ' ' +
      versionTestructuret +
      ' ' +
      structure.version +
      (structure.start_date !== null || structure.end_date !== null
        ? (structure.start_date !== null ? '/' + $filter('date')(structure.start_date, 'yyyy') : '') +
          ' - ' +
          (structure.end_date !== null ? $filter('date')(structure.end_date, 'yyyy') : '')
        : '')
    );
  }
  return {
    getNameWithVersion: getNameWithVersion,
    parseStructureNames: function (structures) {
      structures.forEach(function (structure) {
        structure.name_with_version = getNameWithVersion(structure);
      });
    },
  };
};

export default StructureName;
