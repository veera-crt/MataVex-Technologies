/**
 * Matavex Technologies - Storefront Performance UX
 */

document.addEventListener('DOMContentLoaded', () => {
    console.log('[SYSTEM_BOOT]: Matavex Storefront Initialized.');
    checkLogin();
    initCartUI();
    syncCartQuantity();
});

function checkLogin() {
    const user = localStorage.getItem('matavex_user');
    const loggedInDiv = document.getElementById('logged-in-user');
    const loggedOutDiv = document.getElementById('logged-out-user');
    const nameSpan = document.getElementById('header-user-name');

    if (user && nameSpan && loggedInDiv && loggedOutDiv) {
        try {
            const userData = JSON.parse(user);
            // Index 3 is name, 2 is email
            nameSpan.textContent = userData[3] || userData[2].split('@')[0];

            loggedInDiv.style.display = 'flex';
            loggedOutDiv.style.display = 'none';
        } catch (e) {
            console.error('Auth sync error');
            loggedInDiv.style.display = 'none';
            loggedOutDiv.style.display = 'flex';
        }
    } else if (loggedInDiv && loggedOutDiv) {
        loggedInDiv.style.display = 'none';
        loggedOutDiv.style.display = 'flex';
    }
}

function logout() {
    const modal = document.getElementById('logoutModal');
    if (modal) {
        modal.classList.add('active');
    }
}

function closeLogoutModal() {
    const modal = document.getElementById('logoutModal');
    if (modal) {
        modal.classList.remove('active');
    }
}

function confirmLogout() {
    localStorage.removeItem('matavex_token');
    localStorage.removeItem('matavex_user');
    window.location.reload();
}

// Chat simulation
const chatBtn = document.querySelector('.chat-btn');
if (chatBtn) {
    chatBtn.addEventListener('click', () => {
        alert('Connecting to Matavex Support Node... (Encypted Session)');
    });
}

// Mobile Menu Toggle
const menuBtn = document.querySelector('.mobile-menu-icon');
const closeBtn = document.getElementById('closeDrawer');
const drawer = document.getElementById('mobileDrawer');
const overlay = document.getElementById('drawerOverlay');

const toggleMenu = () => {
    drawer.classList.toggle('active');
    overlay.classList.toggle('active');
    document.body.style.overflow = drawer.classList.contains('active') ? 'hidden' : 'auto';
};

if (menuBtn) menuBtn.addEventListener('click', toggleMenu);
if (closeBtn) closeBtn.addEventListener('click', toggleMenu);
if (overlay) overlay.addEventListener('click', toggleMenu);

// Accordion Logic
const fullStackToggle = document.getElementById('fullStackToggle');
const fullStackContent = document.getElementById('fullStackContent');

if (fullStackToggle) {
    fullStackToggle.addEventListener('click', () => {
        fullStackContent.classList.toggle('active');
        const icon = fullStackToggle.querySelector('ion-icon');
        icon.name = fullStackContent.classList.contains('active') ? 'chevron-up-outline' : 'chevron-down-outline';
    });
}

// Close drawer on link click
document.querySelectorAll('.drawer-links a').forEach(link => {
    link.addEventListener('click', () => {
        if (drawer.classList.contains('active')) toggleMenu();
    });
});

// Header Scroll Effect - Optimized with RequestAnimationFrame
const header = document.querySelector('header');
let scrollTicking = false;

window.addEventListener('scroll', () => {
    if (!scrollTicking) {
        window.requestAnimationFrame(() => {
            if (window.scrollY > 100) {
                header.classList.add('scrolled');
            } else {
                header.classList.remove('scrolled');
            }
            scrollTicking = false;
        });
        scrollTicking = true;
    }
});

// Premium Search Functionality (Inline Expansion)
const searchTrigger = document.getElementById('searchIconTrigger');
const searchInputField = document.getElementById('searchInputField');
const closeSearchInline = document.getElementById('closeSearchInline');
const projectSearchInput = document.getElementById('projectSearchInput');
const serviceCards = document.querySelectorAll('.service-card');
const noResults = document.getElementById('searchNoResults');

if (searchTrigger && searchInputField) {
    searchTrigger.addEventListener('click', () => {
        searchInputField.classList.add('active');
        projectSearchInput.focus();
    });
}

if (closeSearchInline) {
    closeSearchInline.addEventListener('click', () => {
        searchInputField.classList.remove('active');
        projectSearchInput.value = '';
        filterProjects('');
    });
}

// Close search on escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && searchInputField.classList.contains('active')) {
        searchInputField.classList.remove('active');
        projectSearchInput.value = '';
        filterProjects('');
    }
});

if (projectSearchInput) {
    projectSearchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();
        filterProjects(query);
    });
}

function filterProjects(query) {
    let visibleCount = 0;

    serviceCards.forEach(card => {
        const title = card.querySelector('h3').textContent.toLowerCase();
        const desc = card.querySelector('p').textContent.toLowerCase();

        if (title.includes(query) || desc.includes(query)) {
            card.style.display = 'block';
            card.style.animation = 'fadeInUp 0.6s ease forwards';
            visibleCount++;
        } else {
            card.style.display = 'none';
        }
    });

    if (noResults) {
        noResults.style.display = visibleCount === 0 ? 'block' : 'none';
    }
}

// Add fadeInUp animation if it doesn't exist in CSS globally
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
`;
document.head.appendChild(style);

/**
 * handlePayment
 * Secure acquisition flow for premium software
 */
async function handlePayment(id, title, category) {
    console.log(`[QUICK_ACQUISITION]: ${title} in ${category}`);
    const userStr = localStorage.getItem('matavex_user');

    if (!userStr) {
        alert('Please login to acquire this project.');
        window.location.href = 'login.html';
        return;
    }

    // Simplified: For "Buy Now", we just ensure it's in cart and go to checkout
    // This maintains the existing Razorpay flow we built for the cart
    const btn = document.getElementById('modalBuyNow');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="loading-mini"></span> Launching...';
    }

    try {
        // We'll call the existing cart logic silently then immediately redirect
        // This ensures the project is in the cart when we hit /checkout
        await handleAddToCart({ id, name: title }, category, true);
        window.location.href = 'checkout.html';
    } catch (err) {
        console.error('[CORE_FAIL]:', err);
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<ion-icon name="flash-outline"></ion-icon> Buy Now';
        }
    }
}

/**
 * Project Detail Modal System
 */
function createProjectModal() {
    if (document.getElementById('projectDetailModal')) return;

    const modalHTML = `
        <div id="projectDetailModal" class="project-modal">
            <div class="modal-content-wrapper">
                <div class="close-project-modal" onclick="closeProjectModal()">
                    <ion-icon name="close-outline"></ion-icon>
                </div>

                <div class="modal-body">
                    <div class="modal-info">
                        <h1 id="modalTitle">Project Title</h1>
                        <div class="modal-price" id="modalPrice">Rs. 0,000.00</div>
                        <div class="modal-shipping">
                            <span class="link">Shipping</span> calculated at checkout.
                        </div>
                        
                        <div class="modal-actions-group">
                            <button class="btn-add-cart" id="modalAddToCart">Add to cart</button>
                            <button class="btn-buy-now" id="modalBuyNow">Buy it now</button>
                        </div>

                        <div class="modal-description-title">
                            <ion-icon name="information-circle-outline"></ion-icon>
                            Product Description
                        </div>
                        <div class="modal-description-text" id="modalDescription">
                            Loading description...
                        </div>
                    </div>
                    <div class="modal-image-side">
                        <div class="image-branding">
                            <div class="brand-main">MATAVEX CORE</div>
                            <div class="brand-sub">WWW.MATAVEX.TECH</div>
                        </div>
                        <img id="modalImage" src="" alt="Project Image">
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

function showProjectDetails(id, projectsList, category, isInCart = false, isBought = false) {
    createProjectModal();
    const project = projectsList.find(p => p.id === id);
    if (!project) return;

    document.getElementById('modalTitle').textContent = project.name;
    document.getElementById('modalPrice').textContent = `Rs. ${parseFloat(project.offer_amount || project.price).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
    document.getElementById('modalDescription').textContent = project.description || 'Premium industrial project specification.';
    document.getElementById('modalImage').src = project.image_link;

    const addToCartBtn = document.getElementById('modalAddToCart');
    const buyNowBtn = document.getElementById('modalBuyNow');

    if (isBought) {
        addToCartBtn.innerHTML = '<ion-icon name="cloud-done"></ion-icon> In Library';
        addToCartBtn.disabled = true;
        addToCartBtn.style.opacity = '0.7';
        buyNowBtn.innerHTML = '<ion-icon name="open-outline"></ion-icon> View Files';
        buyNowBtn.onclick = () => window.location.href = 'library.html';
    } else if (isInCart) {
        addToCartBtn.innerHTML = '<ion-icon name="checkmark-circle"></ion-icon> Added in card';
        addToCartBtn.disabled = true;
        addToCartBtn.style.opacity = '0.7';
    } else {
        addToCartBtn.innerHTML = '<ion-icon name="cart-outline"></ion-icon> Add to cart';
        addToCartBtn.disabled = false;
        addToCartBtn.style.opacity = '1';
        addToCartBtn.onclick = () => handleAddToCart(project, category);
        buyNowBtn.onclick = () => handlePayment(project.id, project.name, category);
    }

    document.getElementById('projectDetailModal').classList.add('active');
    document.body.style.overflow = 'hidden';
}

/**
 * handleAddToCart
 * Securely add project to user cart in DB
 */
async function handleAddToCart(project, category, silent = false) {
    const userStr = localStorage.getItem('matavex_user');
    if (!userStr) {
        alert('Please login to add items to your cart.');
        window.location.href = 'login.html';
        return;
    }

    const btn = document.getElementById('modalAddToCart');
    if (btn && !silent) {
        btn.disabled = true;
        btn.innerHTML = '<span class="loading-mini"></span> Adding...';
    }

    try {
        const userData = JSON.parse(userStr);
        const userId = userData[0];

        const payload = {
            user_id: userId,
            project_id: project.id,
            project_name: project.name,
            project_category: category === 'redirect-only' ? 'unknown' : category // Fallback
        };

        const response = await fetch('/api/v1/cart', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            const result = await response.json();
            if (!silent) {
                if (result.status === 'exists') {
                    alert(`ℹ️ ${project.name} is already in your cart.`);
                } else {
                    showCartNotification(project.name);
                    syncCartQuantity();
                }
                closeProjectModal();
            }
        } else {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to add to cart');
        }
    } catch (err) {
        console.error('[CART_ERROR]:', err);
        if (!silent) {
            alert('Failed to connect to Matavex Cart Node. Please try again.');
            if (btn) {
                btn.disabled = false;
                btn.textContent = 'Add to cart';
            }
        }
    }
}

function closeProjectModal() {
    const modal = document.getElementById('projectDetailModal');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = 'auto';
    }
}

// Close modal on escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeProjectModal();
});

/**
 * loadProjects
 * Fetch and render projects for a specific category
 */
async function loadProjects(category, gridId) {
    const grid = document.getElementById(gridId);
    if (!grid) return;

    try {
        const userStr = localStorage.getItem('matavex_user');
        let purchasedIds = [];

        if (userStr) {
            const userData = JSON.parse(userStr);
            const res = await fetch(`/api/v1/payments/${userData[0]}`);
            if (res.ok) {
                const boughtP = await res.json();
                purchasedIds = boughtP.map(p => p.project_id);
            }
        }

        const response = await fetch(`/api/v1/projects/${category}`);
        if (!response.ok) throw new Error('Failed to fetch projects');
        const projects = await response.json();

        window[`${category}Projects`] = projects;
        grid.innerHTML = '';

        if (projects.length === 0) {
            grid.innerHTML = '<p style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--color-text-muted);">No projects available in this category.</p>';
            return;
        }

        projects.forEach(project => {
            const isBought = purchasedIds.includes(project.id);
            const card = document.createElement('div');
            card.className = 'product-card';
            card.onclick = () => showProjectDetails(project.id, window[`${category}Projects`], category, false, isBought);

            card.innerHTML = `
                <div class="image-container">
                    ${isBought ? `<span class="product-tag" style="position: absolute; top: 15px; left: 15px; background: #10B981; color: #fff; padding: 4px 12px; border-radius: 5px; font-size: 10px; font-weight: 800; z-index: 5; text-transform: uppercase;">OWNED</span>` : ''}
                    ${project.tag ? `<span class="product-tag" style="position: absolute; top: 15px; right: 15px; background: var(--color-primary); color: #fff; padding: 4px 12px; border-radius: 50px; font-size: 11px; font-weight: 700; z-index: 5;">${project.tag}</span>` : ''}
                    <img src="${project.image_link}" alt="${project.name}" loading="lazy">
                </div>
                <div class="card-footer">
                    <div class="product-title">${project.name}</div>
                    <p style="font-size: 13px; color: var(--color-text-para); margin: 5px 0 15px; line-height: 1.4;">${project.description}</p>
                    <div class="price-container" style="display: flex; align-items: center; gap: 10px; margin-top: auto;">
                        <div class="price-tag">₹${parseFloat(project.offer_amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
                        <div class="original-price" style="text-decoration: line-through; color: var(--color-text-muted); font-size: 13px;">₹${parseFloat(project.original_amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
                        <div class="discount-pill" style="color: #10B981; font-size: 12px; font-weight: 700;">${project.offer_percentage}% OFF</div>
                    </div>
                    <div class="card-action">${isBought ? 'In Library &rarr;' : 'View Details &rarr;'}</div>
                </div>
            `;
            grid.appendChild(card);
        });
    } catch (err) {
        console.error(`[PROJECTS_LOAD_FAIL]: ${category}`, err);
        grid.innerHTML = '<p style="grid-column: 1/-1; text-align: center; padding: 40px; color: #ef4444;">Failed to load projects. Please try again later.</p>';
    }
}
/**
 * Cart UI & Sync Systems
 */
function initCartUI() {
    const cartTrigger = document.querySelector('.cart-trigger');
    if (!cartTrigger) return;

    // 1. Inject Home/Library Icon (left of cart)
    const homeIcon = document.createElement('a');
    homeIcon.href = 'library.html';
    homeIcon.className = 'nav-icon-link';
    homeIcon.innerHTML = '<ion-icon name="home-outline"></ion-icon>';
    homeIcon.title = 'My Purchased Projects';
    homeIcon.style.marginRight = '15px'; // Spacing
    homeIcon.style.fontSize = '24px';
    homeIcon.style.color = 'inherit';
    homeIcon.style.display = 'inline-flex';
    cartTrigger.parentNode.insertBefore(homeIcon, cartTrigger.parentNode.firstChild);

    // 2. Inject Badge with dedicated wrapper for perfect alignment
    const wrapper = document.createElement('div');
    wrapper.className = 'cart-wrapper';
    wrapper.style.position = 'relative';
    wrapper.style.display = 'inline-flex';

    // Store original parent before moving cartTrigger
    const originalParent = cartTrigger.parentNode;

    // Move the icon into the wrapper
    originalParent.insertBefore(wrapper, cartTrigger);
    wrapper.appendChild(cartTrigger);

    const badge = document.createElement('div');
    badge.className = 'cart-badge';
    badge.id = 'cartBadge';
    wrapper.appendChild(badge);

    // 2. Inject Notification Popup
    const notification = document.createElement('div');
    notification.className = 'cart-notification';
    notification.id = 'cartNotification';
    notification.innerHTML = `
        <div class="msg">
            <ion-icon name="checkmark-circle"></ion-icon>
            Project added to cart!
        </div>
        <a href="cart.html" class="btn-checkout">Check Out Now</a>
    `;
    cartTrigger.parentElement.appendChild(notification);

    // 3. Link icon to cart page
    cartTrigger.addEventListener('click', () => {
        window.location.href = 'cart.html';
    });
}

function showCartNotification(projectName) {
    const notification = document.getElementById('cartNotification');
    if (!notification) return;

    notification.classList.add('active');

    // Auto hide after 5 seconds
    setTimeout(() => {
        notification.classList.remove('active');
    }, 5000);
}

async function syncCartQuantity() {
    const userStr = localStorage.getItem('matavex_user');
    const badge = document.getElementById('cartBadge');
    if (!userStr || !badge) {
        if (badge) badge.classList.remove('active');
        return;
    }

    try {
        const userData = JSON.parse(userStr);
        const userId = userData[0];

        const response = await fetch(`/api/v1/cart/${userId}`);
        if (response.ok) {
            const cartItems = await response.json();
            const count = cartItems.length;

            if (count > 0) {
                badge.textContent = count;
                badge.classList.add('active');
            } else {
                badge.classList.remove('active');
            }
        }
    } catch (err) {
        console.warn('[CART_SYNC_FAIL]: Could not sync cart quantity.');
    }
}
