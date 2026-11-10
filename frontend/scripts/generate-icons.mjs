// Deterministic public PNG assets, generated without dependency lifecycle scripts.
import { writeFileSync } from 'node:fs'
import { deflateSync } from 'node:zlib'

function crc32(buffer) {
  let crc = 0xffffffff
  for (const byte of buffer) {
    crc ^= byte
    for (let i = 0; i < 8; i++) crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1))
  }
  return (crc ^ 0xffffffff) >>> 0
}
function chunk(type, data) {
  const name = Buffer.from(type)
  const length = Buffer.alloc(4); length.writeUInt32BE(data.length)
  const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(Buffer.concat([name, data])))
  return Buffer.concat([length, name, data, crc])
}
for (const size of [192, 512]) {
  const pixels = Buffer.alloc((size * 3 + 1) * size)
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    const nx = x / size, ny = y / size
    const white = ((nx - .4) ** 2 + (ny - .36) ** 2 < .019 || (nx - .6) ** 2 + (ny - .36) ** 2 < .019 || (ny > .32 && ny < .55 && nx > .29 && nx < .71) || (ny >= .5 && ny < .76 && Math.abs(nx - .38) < .075 * (.82 - ny) / .32) || (ny >= .5 && ny < .76 && Math.abs(nx - .62) < .075 * (.82 - ny) / .32))
    const offset = y * (size * 3 + 1) + 1 + x * 3
    pixels.set(white ? [255, 255, 255] : [3, 105, 161], offset)
  }
  const header = Buffer.alloc(13); header.writeUInt32BE(size, 0); header.writeUInt32BE(size, 4); header[8] = 8; header[9] = 2
  writeFileSync(new URL(`../public/icon-${size}.png`, import.meta.url), Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', header), chunk('IDAT', deflateSync(pixels)), chunk('IEND', Buffer.alloc(0))]))
}
