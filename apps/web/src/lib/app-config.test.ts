import { describe, expect, it } from "vitest";
import { APP_DESCRIPTION, APP_NAME } from "@/lib/app-config";

describe("app identity", () => {
  it("ships the canonical app name and description", () => {
    expect(APP_NAME).toBe("Image to 3D Asset Library");
    expect(APP_DESCRIPTION).toBe(
      "Turn a single image into a 3D mesh, textures, and a preview render, stored as a versioned asset library on Backblaze B2"
    );
  });
});
