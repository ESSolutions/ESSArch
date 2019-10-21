const structureUnitRelation = () => {
  return {
    getRelatedStructureUnitLinkState(structure_unit) {
      return structure_unit.structure.is_template
        ? 'home.archivalDescriptions.classificationStructures'
        : 'home.archivalDescriptions.search.structure_unit';
    },
    getRelatedStructureUnitLinkParams(structure_unit) {
      return {id: structure_unit.structure.is_template ? structure_unit.structure.id : structure_unit.id};
    },
  };
};

export default structureUnitRelation;
