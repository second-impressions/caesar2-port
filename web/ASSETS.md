# Web UI assets

- `caesar2-background-light.jpg` is an unmodified copy of the [1200 × 613 Caesar II promotional screenshot hosted by MobyGames](https://cdn.mobygames.com/promos/1340513-caesar-ii-screenshot.jpg), used by the light theme because its surround is already white. It was selected over the supplied 800 × 409 Gamekult copy because it has the higher resolution.
- `caesar2-background.jpg` is the dark-theme variant of that same image.
  The only local change is that the white surround outside the city was flood-filled from the four corners to `#0e0c08`, so the shell background blends into the page instead of showing a bright border:

  ```sh
  magick 1340513-caesar-ii-screenshot.jpg -alpha off -fuzz 12% -fill '#0e0c08' \
      -draw 'color 0,0 floodfill' -draw 'color 1199,0 floodfill' \
      -draw 'color 0,612 floodfill' -draw 'color 1199,612 floodfill' \
      -quality 88 caesar2-background.jpg
  ```

  Flood-filling from the corners keeps light pixels inside the city artwork untouched.
- `vendor/pico.min.css` is Pico CSS 2.1.1, distributed under the MIT license in `vendor/PICO-LICENSE.md`.
