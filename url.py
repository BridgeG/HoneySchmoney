def populate_url(url):
    match url:
        case "ab-in-den-urlaub-gutscheine":
            return "https://www.ab-in-den-urlaub.ch/"
        case "aboutyou-gutscheine":
            return "https://www.aboutyou.ch/"
    print("error, no matching url")
    return "url"
