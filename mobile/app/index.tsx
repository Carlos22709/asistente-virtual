/** Redirige la entrada de Expo Router hacia el tablero principal. */

import { Redirect } from "expo-router";

export default function Index() {
  return <Redirect href="/(tabs)" />;
}
