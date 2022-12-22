const injectContainer = `<div class="messages-inject" id="inject"></div>`

const app = new Vue({
    el: '.container',
    data() {
        return {
            injectText: '',
            injectEl: null,
            expandSearch: false,
        };
    },
    methods: {
        peek(event) {
            msg_id = event.target.dataset.id;
//            console.log(msg_id);
            event.target.insertAdjacentHTML('afterend', injectContainer);
            this.injectEl = event.target.nextSibling;
//            .getElementById('inject');
            fetch(`/peek/${msg_id}`)
                .then(response => response.text())
                .then(text => {
                    this.injectText = text;
                    if (this.injectEl === event.target.nextSibling && !this.injectEl.childNodes.length)
                        this.injectEl.insertAdjacentHTML('afterbegin', this.injectText);
                })
                .catch((error) => {
                    console.log(error);
                    this.cleanUp();
                });
        },
        cleanUp() {
            if (this.injectEl) this.injectEl.remove();
            this.injectEl = null;
            this.injectText = '';
        },
        toggleExpand() {
            this.expandSearch = !this.expandSearch;
        }
    },
    computed: {
        isSearch() {
            const route = window.location.pathname;
            return route.startsWith('/search/');
        },
    },
    mounted() {
        this.cleanUp();
    },
});