from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def get_product_recommendations(products, product_id, limit=4):

    if not products:
        return []

    # Product data ko text mein convert karna
    documents = []

    for product in products:

        product_name = product.get("product_name", "")
        description = product.get("description", "")
        category = product.get("category_name", "")
        brand = product.get("brand_name", "")

        text = f"{product_name} {description} {category} {brand}"

        documents.append(text)

    # TF-IDF
    vectorizer = TfidfVectorizer(stop_words="english")

    matrix = vectorizer.fit_transform(documents)

    # Selected product ka index
    selected_index = None

    for index, product in enumerate(products):

        if product["id"] == product_id:
            selected_index = index
            break

    if selected_index is None:
        return []

    # Similarity calculate
    similarity = cosine_similarity(matrix[selected_index : selected_index + 1], matrix)[
        0
    ]

    # Similar products sort
    similar_indexes = similarity.argsort()[::-1]

    recommendations = []

    for index in similar_indexes:

        # Same product ko skip
        if index == selected_index:
            continue

        recommendations.append(products[index])

        if len(recommendations) >= limit:
            break

    return recommendations
