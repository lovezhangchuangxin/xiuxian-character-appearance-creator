# 身体与完整脸提示词

白内搭先定男版，再沿用男版的衣料与着色生成女版。完整脸从同尺度空脸对照补齐。

以下批次使用内置 ImageGen，启用透明背景。参考图按每节所列顺序上传。

## 男版白色交领内搭

1. 整理前留存的男版浅棕试制基体，用于固定站姿和坐标
2. [白色交领原始母版](../references/masters/bodies/original/male.png)
3. [整体画风](../references/style/character-style.png)

[查看输出 · 男版白内搭](../sprites/bodies/male/white.png)

```text
Edit image 1, the existing adult male full-body game sprite, in place on its exact 1024x1536 canvas. Image 1 locks the completely blank bald head, ear and neck coordinates, straight head-on stance and silhouette, empty relaxed hands, original arm contours, legs, bare feet, framing and scale. Image 2 is the original traditional white inner garment reference. Image 3 is the overall clean thin-line Chinese xianxia manhua art style reference. Make a quiet functional white xianxia inner outfit for a modular dress-up base: replace the tan tank and shorts with understated warm ivory white matte linen. The high-coverage fitted sleeveless short wrap top has a very simple overlapping traditional crossover collar, slim shoulder coverage following the existing shoulders, no flared sleeves and no decorative elements; closely fitted modest white upper-thigh undershorts are separate, with short simple hems, no bulk. Keep opacity and modest coverage. The material has low-contrast cool pale gray cel shadows, clean delicate warm-gray outlines, minimal folds, no embroidery, tied sash, cords, lace, shine, trims or modern graphic details. Keep the exact body proportions and pixel positions from image 1 including crown, jaw, shoulders, wrists, knees and soles. Face remains entirely blank and head has no hair. No props, shoes, text, environmental elements, or floor. Transparent alpha outside complete silhouette. One full body only.
```

## 女版白色交领内搭

1. 整理前留存的女版浅棕试制基体，用于固定站姿和坐标
2. [女版身形](../references/masters/bodies/original/female.png)
3. [男版白底衣结构与颜色](../sprites/bodies/male/white.png)
4. [整体画风](../references/style/character-style.png)

[查看输出 · 女版白内搭](../sprites/bodies/female/white.png)

```text
Edit image 1, the adult female blank-face game sprite. Keep its exact 1024x1536 canvas, adult female proportions, pose, skin palette, head crown, ears, jaw, shoulders, relaxed open empty hands, legs, bare feet, coordinates and full extent. Image 2 is the original female template to confirm the female silhouette. Image 3 is the matching final male inner-outfit construction and palette reference: copy the warm ivory matte linen white, low-contrast cool pale gray cel shadows, line weight and simple xianxia crossover collar. Image 4 is the overall art style reference. Replace only the beige camisole and shorts in image 1 with the matching white traditional inner outfit. Adapt the construction to fit within image 1: a fitted sleeveless modest crossover top with narrow shoulder coverage along the existing straps and a clean narrow cross collar, and fitted modest high-waisted short white undershorts, with the exact short hem and shape of image 1. Keep the new collar scaled to the neckline of this female body with no collar protruding beside the neck. Keep the existing upper-thigh exposure for slit dresses, fit along the existing upper-arm boundaries, preserve the leg and arm silhouettes. No decoration, ribbons, outer garments, shoes, face, hair, props, floor, text or backdrop. Real transparent alpha outside silhouette. Output one full-body figure exactly in the first image's position, not a side-by-side.
```

## 男女完整脸

1. [男女空脸同尺度对照](../references/masters/heads/aligned/blank.png)
2. [整体画风](../references/style/character-style.png)

[查看输出 · 男女完整脸对照](../references/masters/heads/aligned/complete.png)

```text
Precise localized edit of image 1: a 1536x1024 aligned pair of bald xianxia game head templates with male on left and female on right. Image 2 is only style guidance for fine soft Chinese xianxia manhua ink lines and economical cel shading, not its poses or character identities. In image 1 add exactly the four missing elements inside each blank face: both eyebrows, both eyes, nose, and mouth. Maintain the exact two columns, head and ear silhouettes, bald skull, facial skin colors, collar edges, zoom, spacing, and all canvas positions. Both straight-on, adult, mature, understated and visually related, calm neutral expression. Male straighter eyebrows and slightly narrow calm eyes, female softly arched eyebrows and gently almond-shaped eyes. Clear thin brown-black lash lines, small warm dark-brown irises with a single tiny highlight, naturally scaled, never doll-like. A simple subtle nose indicated by a tiny warm contour and soft shading, a short understated mouth with delicate line and no lipstick. Keep eyelids visually approximately aligned at y=410 across the combined frame, both eyes balanced across each face center, eyebrows above with comfortable breathing room, nose at y≈493 and mouth at y≈548 with generous distance from chin. Do not introduce hard makeup, 3D rendering, heavy gloss or new skin textures. Both heads are intentionally bald and bare of ornaments. Exact same composition, no additional arms or body, no guides, borders, text or shadows, true transparent outside the contours.
```
