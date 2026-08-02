export const MOTION_DURATION = {
  short: 160,
  medium: 220,
  long: 280,
};
export const MOTION_EASING = {
  enter: 'cubic-bezier(0.16, 1, 0.3, 1)',
  exit: 'cubic-bezier(0.7, 0, 0.84, 0)',
  standard: 'cubic-bezier(0.2, 0, 0, 1)',
};
export const reduceMotionStyles = {
  '@media (prefers-reduced-motion: reduce)': {
    animation: 'none !important',
    transitionDuration: '0.01ms !important',
    scrollBehavior: 'auto !important',
    transform: 'none !important',
  },
};
export const createMotionTransition = (properties, options = {}) => {
  const {
    duration = MOTION_DURATION.medium,
    easing = MOTION_EASING.standard,
    delay = 0,
  } = options;
  const propertyList = Array.isArray(properties) ? properties : [properties];
  return propertyList
    .map((property) => `${property} ${duration}ms ${easing} ${delay}ms`)
    .join(', ');
};