from bs4 import BeautifulSoup

def normalize_bullet_points(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    page_divs = soup.find_all("div")

    for container in page_divs:
        paragraphs = container.find_all("p")
        merged_paragraphs = []
        skip_next = False

        for i, p in enumerate(paragraphs):
            if skip_next:
                skip_next = False
                continue

            if p.get_text(strip=True) in {"•", "●", "-", "‣"} and i + 1 < len(paragraphs):
                next_p = paragraphs[i + 1]
                merged_p = BeautifulSoup(
                    f"<p>• {next_p.get_text(strip=True)}</p>", "html.parser"
                ).p
                merged_paragraphs.append(merged_p)
                skip_next = True
            else:
                cloned_p = BeautifulSoup(f"<p>{p.decode_contents()}</p>", "html.parser").p
                merged_paragraphs.append(cloned_p)

        for child in container.find_all("p"):
            child.decompose()
        for p in merged_paragraphs:
            container.append(p)

    return str(soup)
