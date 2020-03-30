import {Feature} from './types';

let isEnabled = (list: Feature[], featureName: string) => {
  let enabled = false;
  list.forEach((x) => {
    if (x.name === featureName && x.enabled) {
      enabled = true;
    }
  });
  return enabled;
};

let existsAndEnabled = (list: Feature[], featureName: string) => {
  let enabled = false;
  let exists = false;
  list.forEach((x) => {
    if (x.name === featureName) {
      exists = true;
      enabled = x.enabled;
    }
  });
  return !exists || (exists && enabled);
};

export {isEnabled, existsAndEnabled};
