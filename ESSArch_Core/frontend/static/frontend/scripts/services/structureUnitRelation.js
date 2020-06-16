const structureUnitRelation = () => {
  return {
    getRelatedStructureUnitLinkState(structure_unit) {
      return structure_unit.structure.is_template
        ? 'home.archivalDescriptions.classificationStructures'
        : 'home.archivalDescriptions.search.structure_unit';
    },
    getRelatedStructureUnitLinkParams(structure_unit) {
      return {
        id: structure_unit.structure.is_template ? structure_unit.structure.id : structure_unit.id,
        structure: structure_unit.structure.is_template ? null : structure_unit.structure.id,
        archive: structure_unit.structure.is_template ? null : structure_unit.archive,
      };
    },
  };
};

export default structureUnitRelation;
