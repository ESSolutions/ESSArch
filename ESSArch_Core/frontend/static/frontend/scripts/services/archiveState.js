export default function ArchiveState() {
  const state = {selectedId: null};

  return {
    getSelectedId() {
      return state.selectedId;
    },
    setSelectedId(id) {
      state.selectedId = id;
    },
    clear() {
      state.selectedId = null;
    },
  };
}
