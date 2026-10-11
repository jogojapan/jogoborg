// Shared signal: bumping `version` tells the Sources screen (which stays mounted
// across nav clicks) to reset itself to the root of the source browser.
export const sourcesReset = $state({ version: 0 });

export function triggerSourcesReset(): void {
  sourcesReset.version += 1;
}